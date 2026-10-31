from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.schemas.explainable_mastery import ExplainableConceptMasteryResponse
from app.schemas.intervention import StudentInterventionItemOut
from app.schemas.learner import LearnerMasteryItem, LearnerSummaryResponse
from app.schemas.user import UserOut
from app.services.explainable_mastery_service import explainable_mastery_service
from app.services.intervention_service import intervention_service
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


@router.get(
    "/concepts/{concept_id}/explainable",
    response_model=ExplainableConceptMasteryResponse,
    summary="Retrieve explainable concept mastery and evidence breakdown",
)
async def get_explainable_mastery(
    concept_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> ExplainableConceptMasteryResponse:
    return await explainable_mastery_service.get_concept_explainable_mastery(
        session, current_user.id, concept_id
    )


@router.get(
    "/interventions",
    response_model=list[StudentInterventionItemOut],
    summary="List active assigned interventions for the current student",
)
async def get_my_interventions(
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> list[StudentInterventionItemOut]:
    return await intervention_service.get_student_interventions(session, current_user.id)


@router.post(
    "/interventions/{assignment_id}/complete",
    status_code=204,
    summary="Record student completion of an assigned intervention",
)
async def complete_my_intervention(
    assignment_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> None:
    await intervention_service.complete_student_intervention(
        session, current_user.id, assignment_id
    )
