import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, status

from app.config import get_settings
from app.schemas import StoreConfigResponse

logger = logging.getLogger("app.api.store_config")
router = APIRouter(tags=["store-config"])

POLICY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "policy"


@router.get("/config", response_model=StoreConfigResponse)
async def get_store_config() -> StoreConfigResponse:
    settings = get_settings()
    return StoreConfigResponse(
        env=settings.APP_ENV,
        dev_tools=settings.APP_ENV in ("dev", "test"),
        voice_enabled=bool(settings.STT_PROVIDER),
        voice_max_seconds=settings.VOICE_MAX_SECONDS,
        store_name=settings.STORE_NAME,
        refund_auto_approve_limit_inr=settings.REFUND_AUTO_APPROVE_LIMIT_INR,
        return_window_days=settings.RETURN_WINDOW_DAYS,
    )


@router.get("/policy/{lang}")
async def get_policy(lang: str) -> Response:
    clean_lang = lang.lower().strip()
    if clean_lang in ("ta", "tamil", "tanglish"):
        filename = "returns_policy_ta.md"
    else:
        filename = "returns_policy_en.md"

    file_path = POLICY_DIR / filename
    if not file_path.exists():
        # Fallback to English if Tamil doesn't exist
        file_path = POLICY_DIR / "returns_policy_en.md"

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy document not found.",
        )

    content = file_path.read_text(encoding="utf-8")
    return Response(content=content, media_type="text/markdown; charset=utf-8")
