from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.schemas.review import ReviewDueItem
from app.schemas.user import UserOut
from app.services.review_service import review_service

router = APIRouter(prefix="/reviews", tags=["Spaced Repetition Reviews"])


@router.get("/due", response_model=list[ReviewDueItem])
async def get_due_reviews(
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> list[ReviewDueItem]:
    """Retrieve biological concepts due for spaced review, prioritized by SM-2 delay and decay."""
    return await review_service.get_due_reviews(session, current_user.id)

