import logging
import time
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models import ChatMessage, ChatSession, Customer, Escalation, EscalationEvent, Trace
from app.prompts import FALLBACK_REPLY_EN_TA
from app.schemas import ChatResponse, RouterOutput, SourceItem
from app.services.generator import generate_response
from app.services.llm import GroqLLMClient
from app.services.rag import retrieve_policy_context, retrieve_product_context
from app.services.router import classify_message
from app.services.tools import (
    check_refund_eligibility,
    create_refund,
    get_order_status,
    list_customer_orders,
)

logger = logging.getLogger("app.services.pipeline")


async def record_escalation(
    session: AsyncSession,
    session_id: UUID,
    customer_id: UUID,
    reason: str,
    reason_type: str,
    priority: str = "normal",
    refund_id: UUID | None = None,
) -> Escalation:
    """
    Idempotently find an active escalation for this session or create a new one.
    Guarantees at most ONE active (open or in_progress) escalation per session.
    Writes a 'created' audit event when a new escalation is created.
    """
    esc_stmt = (
        select(Escalation)
        .where(
            Escalation.session_id == session_id,
            Escalation.status.in_(["open", "in_progress"]),
        )
        .with_for_update()
    )
    existing = (await session.execute(esc_stmt)).scalar_one_or_none()

    if existing:
        if priority == "high":
            existing.priority = "high"
        if refund_id:
            existing.refund_id = refund_id
        if reason_type == "refund_pending_approval":
            existing.reason_type = reason_type
        return existing

    new_esc = Escalation(
        session_id=session_id,
        customer_id=customer_id,
        reason=reason,
        reason_type=reason_type,
        status="open",
        priority=priority,
        refund_id=refund_id,
        version=1,
    )
    session.add(new_esc)
    await session.flush()

    audit_event = EscalationEvent(
        escalation_id=new_esc.id,
        actor_type="system",
        actor_id=None,
        action="created",
        detail={"reason_type": reason_type, "priority": priority},
    )
    session.add(audit_event)
    await session.flush()
    return new_esc


async def handle_message(
    session: AsyncSession,
    customer_id: UUID | None,
    session_id: UUID | None,
    text: str,
    channel: str = "web",
    input_mode: str = "text",
    anon_token: str | None = None,
    context: dict[str, Any] | None = None,
    llm_client: GroqLLMClient | None = None,
    settings: Settings | None = None,
) -> ChatResponse:
    """
    Core pipeline orchestrator for customer messages.
    Deterministic handlers control DB access; LLM only classifies and generates text.
    Always writes a trace row, even on failure.
    Supports authenticated customers and anonymous visitors (via anon_token),
    context pinning (product/order), and deterministic client actions.
    """
    from app.auth.security import hash_session_token

    cfg = settings or get_settings()
    client = llm_client or GroqLLMClient(cfg)
    pipeline_start_time = time.monotonic()

    # Step 1: Validation
    cleaned_text = text.strip()
    if not cleaned_text:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")
    if len(text) > cfg.MAX_MESSAGE_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"Message exceeds maximum allowed length of {cfg.MAX_MESSAGE_CHARS} characters.",
        )

    # Verify customer if authenticated
    customer: Customer | None = None
    if customer_id is not None:
        customer_stmt = select(Customer).where(Customer.id == customer_id)
        customer = (await session.execute(customer_stmt)).scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found.")

    # Validate or create chat session
    anon_token_hash = hash_session_token(anon_token) if anon_token else None

    if session_id is None:
        # Check if an active anonymous session exists for this anon token
        if customer_id is None and anon_token_hash:
            s_stmt = (
                select(ChatSession)
                .where(
                    ChatSession.anon_token_hash == anon_token_hash,
                    ChatSession.customer_id.is_(None),
                )
                .order_by(ChatSession.created_at.desc())
                .limit(1)
            )
            chat_session = (await session.execute(s_stmt)).scalar_one_or_none()
            if chat_session is None:
                chat_session = ChatSession(
                    customer_id=None,
                    anon_token_hash=anon_token_hash,
                    channel=channel,
                )
                session.add(chat_session)
                await session.flush()
        else:
            chat_session = ChatSession(
                customer_id=customer_id,
                anon_token_hash=anon_token_hash,
                channel=channel,
            )
            session.add(chat_session)
            await session.flush()
    else:
        session_stmt = select(ChatSession).where(ChatSession.id == session_id)
        chat_session = (await session.execute(session_stmt)).scalar_one_or_none()
        if chat_session is None:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        # If session belonged to anonymous user and now we have authenticated customer, claim it
        if chat_session.customer_id is None and customer_id is not None:
            chat_session.customer_id = customer_id
        elif customer_id is not None and chat_session.customer_id != customer_id:
            raise HTTPException(status_code=403, detail="Session does not belong to this customer.")

    # Step 2: Store user message & load history
    user_msg = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content=cleaned_text,
        input_mode=input_mode,
    )
    session.add(user_msg)
    await session.flush()

    # CHECK HUMAN HANDLING: If an escalation is already in_progress, hold the customer without LLM calls
    in_progress_stmt = select(Escalation).where(
        Escalation.session_id == chat_session.id,
        Escalation.status == "in_progress",
    )
    in_progress_esc = (await session.execute(in_progress_stmt)).scalar_one_or_none()

    if in_progress_esc:
        holding_reply = (
            "A support executive is handling your request and will reply here. / "
            "ஒரு ஆதரவு நிர்வாகி உங்கள் கோரிக்கையைக் கவனித்து இங்கே பதிலளிப்பார்."
        )
        assistant_msg = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=holding_reply,
            input_mode="text",
        )
        session.add(assistant_msg)
        await session.flush()

        latency_ms = int((time.monotonic() - pipeline_start_time) * 1000)
        trace = Trace(
            session_id=chat_session.id,
            user_message_id=user_msg.id,
            intent="human_handling",
            language="en",
            router_raw={"intent": "human_handling", "escalation_id": str(in_progress_esc.id)},
            tool_calls=[],
            final_answer=holding_reply,
            models={},
            prompt_tokens=0,
            completion_tokens=0,
            cost_inr=Decimal("0.0000"),
            latency_ms=latency_ms,
            error=None,
        )
        session.add(trace)
        await session.commit()
        await session.refresh(trace)

        return ChatResponse(
            session_id=chat_session.id,
            reply=holding_reply,
            intent="human_handling",
            language="en",
            requires_human=True,
            trace_id=trace.id,
            sources=[],
            suggested_actions=[],
            structured_output=None,
        )

    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == chat_session.id, ChatMessage.id != user_msg.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(cfg.HISTORY_TURNS)
    )
    history_records = list((await session.execute(history_stmt)).scalars().all())
    history_records.reverse()
    history = [{"role": msg.role, "content": msg.content} for msg in history_records]

    # Tracking metrics for the trace
    tool_calls: list[dict[str, Any]] = []
    response_sources: list[SourceItem] = []
    models_used: dict[str, str] = {
        "router": cfg.ROUTER_MODEL,
        "generator": cfg.GENERATOR_MODEL,
    }
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost_inr = Decimal("0.0000")
    pipeline_error: str | None = None
    requires_human = False

    # Step 3: ROUTER
    try:
        router_output, router_raw, router_llm_resp, router_err = await classify_message(
            llm_client=client,
            message=cleaned_text,
            history=history,
            settings=cfg,
        )
        total_prompt_tokens += router_llm_resp.prompt_tokens
        total_completion_tokens += router_llm_resp.completion_tokens
        total_cost_inr += router_llm_resp.cost_inr
        if router_err:
            pipeline_error = router_err
    except Exception as exc:
        logger.exception("Router failure: %s", exc)
        router_output = RouterOutput(
            intent="escalate",
            language="en",
            order_number=None,
            refund_reason=None,
            search_query=None,
            category=None,
            max_price_inr=None,
        )
        router_raw = {"intent": "escalate", "error": str(exc)}
        pipeline_error = f"Router fatal error: {exc}"

    intent = router_output.intent
    language = router_output.language
    order_number = router_output.order_number
    refund_reason = router_output.refund_reason

    # Apply context pinning if provided
    pinned_product_id: str | None = None
    if context:
        ctx_type = context.get("type")
        ctx_id = context.get("id")
        if ctx_type == "order" and not order_number and ctx_id:
            order_number = str(ctx_id).strip()
        elif ctx_type == "product" and ctx_id:
            pinned_product_id = str(ctx_id).strip()

    actions: list[dict[str, Any]] = []

    # Step 4: TOOLS & RAG RETRIEVAL
    # Check if anonymous user is attempting authenticated actions
    if customer_id is None and intent in ("order_status", "refund_request"):
        reply_text = (
            "Please sign in to your account to view your order status or request a return. / "
            "உங்கள் ஆர்டர் விவரங்களைப் பார்க்க அல்லது திரும்பப் பெற உங்கள் கணக்கில் உள்நுழையவும்."
            if language in ("ta", "tanglish")
            else "Please sign in to your account to view your order details or request a return."
        )
        actions.append({"type": "open_login", "payload": {}})
        assistant_msg = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=reply_text,
            input_mode="text",
        )
        session.add(assistant_msg)
        await session.flush()

        latency_ms = int((time.monotonic() - pipeline_start_time) * 1000)
        trace = Trace(
            session_id=chat_session.id,
            user_message_id=user_msg.id,
            intent=intent,
            language=language,
            router_raw=router_raw,
            tool_calls=[],
            final_answer=reply_text,
            models=models_used,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            cost_inr=total_cost_inr,
            latency_ms=latency_ms,
            error=None,
        )
        session.add(trace)
        await session.commit()
        await session.refresh(trace)

        return ChatResponse(
            session_id=chat_session.id,
            reply=reply_text,
            intent=intent,
            language=language,
            requires_human=False,
            trace_id=trace.id,
            sources=[],
            suggested_actions=["Sign In", "View Products", "Return Policy"],
            actions=actions,
            structured_output=None,
        )

    tool_result: dict[str, Any]

    if intent == "order_status":
        if not order_number:
            tool_result = await list_customer_orders(session, customer_id, limit=5)
            tool_calls.append({"tool": "list_customer_orders", "input": {"limit": 5}, "output": tool_result})
        else:
            tool_result = await get_order_status(session, customer_id, order_number)
            tool_calls.append(
                {"tool": "get_order_status", "input": {"order_number": order_number}, "output": tool_result}
            )

    elif intent == "refund_request":
        if not order_number:
            tool_result = {
                "status": "missing_order_number",
                "message": "Order number is required to process refund. Ask customer for order number.",
            }
            tool_calls.append(
                {"tool": "refund_request", "input": {"order_number": None}, "output": tool_result}
            )
        else:
            eligibility = await check_refund_eligibility(
                session, customer_id, order_number, cfg.RETURN_WINDOW_DAYS
            )
            tool_calls.append(
                {
                    "tool": "check_refund_eligibility",
                    "input": {"order_number": order_number},
                    "output": eligibility,
                }
            )

            if not eligibility.get("eligible"):
                tool_result = eligibility
            else:
                refund_res = await create_refund(
                    session=session,
                    customer_id=customer_id,
                    order_number=order_number,
                    refund_reason=refund_reason,
                    auto_approve_limit=cfg.REFUND_AUTO_APPROVE_LIMIT_INR,
                    session_id=chat_session.id,
                )
                tool_result = refund_res
                requires_human = refund_res.get("requires_human", False)
                tool_calls.append(
                    {
                        "tool": "create_refund",
                        "input": {"order_number": order_number, "reason": refund_reason},
                        "output": refund_res,
                    }
                )

    elif intent == "policy_question":
        p_query = router_output.search_query or cleaned_text
        tool_result, sources, trace_entry = await retrieve_policy_context(
            session=session,
            query=p_query,
            language=language,
            top_k=cfg.RAG_TOP_K,
            min_score=cfg.RAG_MIN_SCORE,
        )
        tool_calls.append(trace_entry)
        response_sources.extend(sources)

    elif intent == "product_question":
        p_query = router_output.search_query or cleaned_text
        tool_result, sources, trace_entry = await retrieve_product_context(
            session=session,
            search_query=p_query,
            category=router_output.category,
            max_price=router_output.max_price_inr,
            top_k=cfg.RAG_TOP_K,
            min_score=cfg.RAG_MIN_SCORE,
        )
        tool_calls.append(trace_entry)
        response_sources.extend(sources)
        if sources:
            actions.append({"type": "view_product", "payload": {"product_id": sources[0].id}})
        elif pinned_product_id:
            actions.append({"type": "view_product", "payload": {"product_id": pinned_product_id}})

    elif intent == "escalate":
        r_type = (
            "router_fallback" if pipeline_error and "router" in pipeline_error.lower() else "user_requested"
        )
        escalation = await record_escalation(
            session=session,
            session_id=chat_session.id,
            customer_id=customer_id or customer_id,  # customer_id can be UUID
            reason=f"Customer request / bot escalation. Last input: {cleaned_text[:200]}",
            reason_type=r_type,
            priority="normal",
        )
        requires_human = True
        tool_result = {
            "status": "escalated",
            "escalation_id": str(escalation.id),
            "message": "Conversation escalated to human support executive.",
        }
        tool_calls.append(
            {"tool": "create_escalation", "input": {"reason": escalation.reason}, "output": tool_result}
        )
        actions.append({"type": "show_escalation", "payload": {"status": "handed_to_support"}})

    else:  # smalltalk
        tool_result = {
            "status": "smalltalk",
            "message": "Politely greet and steer customer to available services (order tracking, refunds).",
        }
        tool_calls.append({"tool": "smalltalk", "input": {}, "output": tool_result})

    # Step 5: GENERATOR
    final_reply: str
    suggested_actions: list[str] = []
    structured_output: Any = None
    try:
        gen_output, gen_llm_resp = await generate_response(
            llm_client=client,
            user_message=cleaned_text,
            language=language,
            tool_result=tool_result,
            history=history,
            intent=intent,
            settings=cfg,
        )
        final_reply = gen_output.reply
        suggested_actions = gen_output.suggested_actions
        structured_output = gen_output
        total_prompt_tokens += gen_llm_resp.prompt_tokens
        total_completion_tokens += gen_llm_resp.completion_tokens
        total_cost_inr += gen_llm_resp.cost_inr
    except Exception as exc:
        logger.exception("Generator failure: %s", exc)
        pipeline_error = (
            f"{pipeline_error}; Generator fatal error: {exc}"
            if pipeline_error
            else f"Generator fatal error: {exc}"
        )
        final_reply = FALLBACK_REPLY_EN_TA
        requires_human = True

        # Escalate on fatal generator failure only if not already escalated this turn
        if not any(call.get("tool") == "create_escalation" for call in tool_calls):
            await record_escalation(
                session=session,
                session_id=chat_session.id,
                customer_id=customer_id,
                reason=f"LLM failure fallback: {exc}",
                reason_type="llm_failure",
                priority="normal",
            )

    # Step 6: Store Assistant message
    assistant_msg = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content=final_reply,
        input_mode="text",
    )
    session.add(assistant_msg)
    await session.flush()

    # Step 7: Store Trace
    latency_ms = int((time.monotonic() - pipeline_start_time) * 1000)
    trace = Trace(
        session_id=chat_session.id,
        user_message_id=user_msg.id,
        intent=intent,
        language=language,
        router_raw=router_raw,
        tool_calls=tool_calls,
        final_answer=final_reply,
        models=models_used,
        prompt_tokens=total_prompt_tokens,
        completion_tokens=total_completion_tokens,
        cost_inr=total_cost_inr,
        latency_ms=latency_ms,
        error=pipeline_error,
    )
    session.add(trace)
    await session.commit()
    await session.refresh(trace)

    return ChatResponse(
        session_id=chat_session.id,
        reply=final_reply,
        intent=intent,
        language=language,
        requires_human=requires_human,
        trace_id=trace.id,
        sources=response_sources,
        suggested_actions=suggested_actions,
        actions=actions,
        structured_output=structured_output,
    )
