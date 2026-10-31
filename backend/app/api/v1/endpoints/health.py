from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(tags=["Health & Readiness"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Fast liveness probe with zero external dependencies."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(
    session: AsyncSession = Depends(get_db_session),
) -> ReadyResponse:
    """Readiness probe checking database connectivity and configuration sanity."""
    settings = get_settings()

    db_status = "connected"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database check failed: {db_status}",
        )

    return ReadyResponse(
        status="ok",
        database=db_status,
        environment=settings.ENV,
        primary_model=settings.LLM_PRIMARY_MODEL,
        available_fallback_models=settings.fallback_models_list,
    )
