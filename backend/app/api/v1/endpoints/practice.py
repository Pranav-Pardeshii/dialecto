from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.schemas.practice import (
    PracticeAnswerRequest,
    PracticeAnswerResponse,
    PracticeNextRequest,
    PracticeNextResponse,
)
from app.schemas.user import UserOut
from app.services.practice_service import practice_service

router = APIRouter(prefix="/practice", tags=["Practice"])


@router.post("/next", response_model=PracticeNextResponse)
async def get_next_practice_question(
    req: PracticeNextRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> PracticeNextResponse:
    """Fetch next targeted question calibrated to ~70% expected success with selection rationale."""
    return await practice_service.get_next_question(session, current_user.id, req)


@router.post("/answers", response_model=PracticeAnswerResponse)
async def submit_practice_answer(
    req: PracticeAnswerRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> PracticeAnswerResponse:
    """Submit an answer to a practice question with atomic Bayesian mastery and SM-2 updates."""
    return await practice_service.submit_answer(session, current_user.id, req)
