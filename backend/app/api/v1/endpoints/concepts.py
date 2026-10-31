from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DEMO_USERS
from app.db.session import get_db_session
from app.schemas.concept import ConceptDetailResponse, ConceptGraphResponse
from app.schemas.user import UserOut
from app.services.concept_service import concept_service

router = APIRouter(prefix="/concepts", tags=["Concepts"])


async def get_optional_user(
    x_demo_user_id: int | None = Header(default=None, alias="X-Demo-User-Id"),
) -> UserOut | None:
    if x_demo_user_id and x_demo_user_id in DEMO_USERS:
        return DEMO_USERS[x_demo_user_id]
    return None


@router.get("", response_model=ConceptGraphResponse)
async def get_concept_graph(
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut | None = Depends(get_optional_user),
) -> ConceptGraphResponse:
    """Retrieve full concept graph (nodes with mastery and directed prerequisite edges)."""
    return await concept_service.get_concept_graph(session, current_user)


@router.get("/{concept_id}", response_model=ConceptDetailResponse)
async def get_concept_detail(
    concept_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ConceptDetailResponse:
    """Retrieve individual concept details and lesson markdown (excludes rubric key points)."""
    return await concept_service.get_concept_detail(session, concept_id)
