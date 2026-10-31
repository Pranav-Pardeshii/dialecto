from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.llm.client import verify_available_models
from app.ai.llm.recorder import recorder
from app.api.v1.endpoints import health
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, global_exception_handler
from app.core.logging import setup_logging
from app.core.middleware import RequestTracingMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    settings = get_settings()
    recorder.start()
    logger.info(
        "app_startup",
        env=settings.ENV,
        primary_model=settings.LLM_PRIMARY_MODEL,
        fallbacks=settings.fallback_models_list,
    )
    # Check model availability non-blockingly
    try:
        import asyncio

        asyncio.create_task(verify_available_models())
    except Exception as exc:
        logger.warning("model_verification_schedule_failed", error=str(exc))

    yield

    logger.info("app_shutdown")
    await recorder.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Dialecto API",
        version="0.1.0",
        docs_url="/docs" if settings.ENV != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(RequestTracingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error Handlers
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, global_exception_handler)

    # Health & Readiness (root level per docs/api.md)
    app.include_router(health.router)

    # API v1
    app.include_router(api_v1_router)

    return app


app = create_app()
