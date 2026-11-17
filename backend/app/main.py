import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.admin_auth import router as admin_auth_router
from app.api.admin_cases import (
    public_router as public_session_router,
)
from app.api.admin_cases import (
    router as admin_cases_router,
)
from app.api.admin_escalations import (
    router as admin_escalations_router,
)
from app.api.admin_operations import router as admin_operations_router
from app.api.cart import router as cart_router
from app.api.chat import router as chat_router
from app.api.customer_auth import router as customer_auth_router
from app.api.customers import router as customers_router
from app.api.debug import router as debug_router
from app.api.health import router as health_router
from app.api.orders import router as orders_router
from app.api.products import categories_router
from app.api.products import router as products_router
from app.api.store_config import router as store_config_router
from app.config import get_settings
from app.db import engine

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "name":"%(name)s", "level":"%(levelname)s", "message":"%(message)s"}',
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    import asyncio

    from app.services.embeddings import get_embedder

    async def _bg_warm():
        try:
            embedder = get_embedder()
            await asyncio.to_thread(embedder._load_model)
            logger.info("Embedding model pre-warmed successfully in background.")
        except Exception as e:
            logger.warning("Could not pre-warm embedding model in background: %s", e)

    asyncio.create_task(_bg_warm())
    yield
    logger.info("Application shutting down...")
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    is_dev = settings.APP_ENV.lower() == "dev"
    app = FastAPI(
        title="Regional E-Commerce Support Assistant API",
        version="1.0.0",
        docs_url="/docs" if is_dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if is_dev else None,
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Request ID and Structured Logging Middleware
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        start_time = time.monotonic()

        path = request.url.path
        method = request.method
        content_length = request.headers.get("content-length", "0")
        logger.info(
            f'request_started request_id="{req_id}" method="{method}" path="{path}" bytes={content_length}'
        )

        try:
            response = await call_next(request)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            response.headers["X-Request-ID"] = req_id
            logger.info(
                f'request_completed request_id="{req_id}" status={response.status_code} latency_ms={elapsed_ms}'
            )
            return response
        except (StarletteHTTPException, RequestValidationError):
            # Re-raise Starlette / FastAPI HTTP and validation exceptions so FastAPI's exception handlers format them
            raise
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.exception(f'request_failed request_id="{req_id}" error="{exc}" latency_ms={elapsed_ms}')
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
                headers={"X-Request-ID": req_id},
            )

    # Custom Exception Handlers for standard Admin error format: {"error": {"code": str, "message": str}}
    @app.exception_handler(StarletteHTTPException)
    async def admin_http_exception_handler(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/admin"):
            code = "error"
            message = str(exc.detail)
            if isinstance(exc.detail, dict):
                code = exc.detail.get("code", "error")
                message = exc.detail.get("message", str(exc.detail))
            elif exc.status_code == 401:
                code = "invalid_credentials"
            elif exc.status_code == 403:
                code = "forbidden"
            elif exc.status_code == 404:
                code = "not_found"
            elif exc.status_code == 409:
                code = "conflict"
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": {"code": code, "message": message}},
                headers={"Cache-Control": "no-store"},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # Router registration
    app.include_router(health_router, tags=["Health"])
    app.include_router(customer_auth_router)
    app.include_router(store_config_router)
    app.include_router(categories_router)
    app.include_router(products_router)
    app.include_router(cart_router)
    app.include_router(orders_router)
    app.include_router(chat_router, tags=["Chat"])
    app.include_router(debug_router, tags=["Debug"])
    app.include_router(admin_auth_router)
    app.include_router(admin_operations_router)
    app.include_router(admin_cases_router)
    app.include_router(admin_escalations_router)
    app.include_router(public_session_router)

    if is_dev:
        app.include_router(customers_router, tags=["Demo Customers"])
        logger.info("Demo customers route registered at /customers/demo (APP_ENV=dev)")

    return app


app = create_app()
