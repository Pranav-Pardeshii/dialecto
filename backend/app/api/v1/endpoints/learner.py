from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.schemas.learner import LearnerMasteryItem, LearnerSummaryResponse
from app.schemas.user import UserOut
from app.services.learner_service import learner_service

router = APIRouter(prefix="/learner", tags=["Learner"])


@router.get("/mastery", response_model=list[LearnerMasteryItem])
async def get_learner_mastery(
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> list[LearnerMasteryItem]:
    """Retrieve full per-concept mastery details for current student."""
    return await learner_service.get_mastery_list(session, current_user.id)


@router.get("/summary", response_model=LearnerSummaryResponse)
async def get_learner_summary(
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> LearnerSummaryResponse:
    """Retrieve high-level learner summary (overall mastery, weakest concepts, due reviews, active misconceptions)."""
    return await learner_service.get_summary(session, current_user.id)
