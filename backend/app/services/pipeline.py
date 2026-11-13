import logging
import time
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models import ChatMessage, ChatSession, Customer, Escalation, Trace
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


async def handle_message(
    session: AsyncSession,
    customer_id: UUID,
    session_id: UUID | None,
    text: str,
    channel: str = "web",
    llm_client: GroqLLMClient | None = None,
    settings: Settings | None = None,
) -> ChatResponse:
    """
    Core pipeline orchestrator for customer messages.
    Deterministic handlers control DB access; LLM only classifies and generates text.
    Always writes a trace row, even on failure.
    """
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

    # Verify customer exists
    customer_stmt = select(Customer).where(Customer.id == customer_id)
    customer = (await session.execute(customer_stmt)).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found.")

    # Validate or create chat session
    if session_id is None:
        chat_session = ChatSession(customer_id=customer_id, channel=channel)
        session.add(chat_session)
        await session.flush()
    else:
        session_stmt = select(ChatSession).where(ChatSession.id == session_id)
        chat_session = (await session.execute(session_stmt)).scalar_one_or_none()
        if chat_session is None:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        if chat_session.customer_id != customer_id:
            raise HTTPException(status_code=403, detail="Session does not belong to this customer.")

    # Step 2: Store user message & load history
    user_msg = ChatMessage(session_id=chat_session.id, role="user", content=cleaned_text)
    session.add(user_msg)
    await session.flush()

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
        )
        router_raw = {"error": str(exc)}
        pipeline_error = f"Router fatal exception: {exc}"

    intent = router_output.intent
    language = router_output.language
    order_number = router_output.order_number
    refund_reason = router_output.refund_reason

    # Step 4: HANDLERS (deterministic)
    tool_result: dict[str, Any] = {}

    if intent == "order_status":
        if not order_number:
            orders_res = await list_customer_orders(session, customer_id)
            if orders_res.get("status") == "found_orders":
                tool_result = orders_res
                tool_calls.append(
                    {
                        "tool": "list_customer_orders",
                        "input": {"customer_id": str(customer_id)},
                        "output": tool_result,
                    }
                )
            else:
                tool_result = {
                    "status": "missing_order_number",
                    "message": "Order number was not specified. Ask customer for order number.",
                }
                tool_calls.append(
                    {"tool": "order_status", "input": {"order_number": None}, "output": tool_result}
                )
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

    elif intent == "escalate":
        escalation = Escalation(
            session_id=chat_session.id,
            reason=f"Customer request / bot escalation. Last input: {cleaned_text[:200]}",
            status="open",
        )
        session.add(escalation)
        await session.flush()
        requires_human = True
        tool_result = {
            "status": "escalated",
            "escalation_id": str(escalation.id),
            "message": "Conversation escalated to human support executive.",
        }
        tool_calls.append(
            {"tool": "create_escalation", "input": {"reason": escalation.reason}, "output": tool_result}
        )

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
            escalation = Escalation(
                session_id=chat_session.id,
                reason=f"LLM failure fallback: {exc}",
                status="open",
            )
            session.add(escalation)
            await session.flush()

    # Step 6: Store Assistant message
    assistant_msg = ChatMessage(session_id=chat_session.id, role="assistant", content=final_reply)
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
        structured_output=structured_output,
    )
