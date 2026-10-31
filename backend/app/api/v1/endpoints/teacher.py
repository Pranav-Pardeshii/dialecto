from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_teacher, verify_classroom_access
from app.db.session import get_db_session
from app.schemas.explainable_mastery import ExplainableConceptMasteryResponse
from app.schemas.intervention import (
    InterventionAssignRequest,
    InterventionCreateRequest,
    InterventionDetailOut,
    InterventionOutcomesResponse,
    InterventionRecommendationOut,
)
from app.schemas.teacher import (
    AtRiskStudentItem,
    CurriculumGapItem,
    MisconceptionPrevalenceItem,
    StudentDetailResponse,
    TeacherHeatmapResponse,
)
from app.schemas.user import UserOut
from app.services.explainable_mastery_service import explainable_mastery_service
from app.services.intervention_service import intervention_service
from app.services.teacher_service import teacher_service

router = APIRouter(prefix="/teacher", tags=["Teacher Analytics"])


@router.get("/classrooms/{classroom_id}/heatmap", response_model=TeacherHeatmapResponse)
async def get_classroom_heatmap(
    classroom_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> TeacherHeatmapResponse:
    """Retrieve full 30x20 student-concept effective mastery matrix."""
    verify_classroom_access(current_teacher, classroom_id)
    return await teacher_service.get_heatmap(session, classroom_id)


@router.get("/classrooms/{classroom_id}/gaps", response_model=list[CurriculumGapItem])
async def get_classroom_gaps(
    classroom_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> list[CurriculumGapItem]:
    """Retrieve concepts ranked by classroom failure rate and average mastery."""
    verify_classroom_access(current_teacher, classroom_id)
    return await teacher_service.get_curriculum_gaps(session, classroom_id)


@router.get(
    "/classrooms/{classroom_id}/misconceptions", response_model=list[MisconceptionPrevalenceItem]
)
async def get_classroom_misconceptions(
    classroom_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> list[MisconceptionPrevalenceItem]:
    """Retrieve classroom misconceptions sorted by prevalence across students."""
    verify_classroom_access(current_teacher, classroom_id)
    return await teacher_service.get_misconception_prevalence(session, classroom_id)


@router.get("/classrooms/{classroom_id}/at-risk", response_model=list[AtRiskStudentItem])
async def get_at_risk_students(
    classroom_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> list[AtRiskStudentItem]:
    """Retrieve list of students at risk due to critical misconceptions or low mastery."""
    verify_classroom_access(current_teacher, classroom_id)
    return await teacher_service.get_at_risk_students(session, classroom_id)


@router.get(
    "/classrooms/{classroom_id}/students/{student_id}", response_model=StudentDetailResponse
)
async def get_student_drilldown(
    classroom_id: int,
    student_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> StudentDetailResponse:
    """Retrieve deep dive into a student's concept masteries and active misconceptions."""
    verify_classroom_access(current_teacher, classroom_id)
    return await teacher_service.get_student_detail(session, classroom_id, student_id)


@router.get(
    "/classrooms/{classroom_id}/students/{student_id}/concepts/{concept_id}/explainable",
    response_model=ExplainableConceptMasteryResponse,
    summary="Retrieve explainable concept mastery and evidence timeline for a student",
)
async def get_student_concept_explainable_mastery(
    classroom_id: int,
    student_id: int,
    concept_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> ExplainableConceptMasteryResponse:
    verify_classroom_access(current_teacher, classroom_id)
    return await explainable_mastery_service.get_concept_explainable_mastery(
        session, student_id, concept_id
    )


@router.get(
    "/classrooms/{classroom_id}/interventions/recommendations",
    response_model=list[InterventionRecommendationOut],
    summary="Get data-driven intervention recommendations based on real classroom learning gaps",
)
async def get_intervention_recommendations(
    classroom_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> list[InterventionRecommendationOut]:
    verify_classroom_access(current_teacher, classroom_id)
    return await intervention_service.get_recommendations(session, classroom_id)


@router.get(
    "/classrooms/{classroom_id}/interventions",
    response_model=list[InterventionDetailOut],
    summary="List all interventions for a classroom",
)
async def list_interventions(
    classroom_id: int,
    status_filter: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> list[InterventionDetailOut]:
    verify_classroom_access(current_teacher, classroom_id)
    return await intervention_service.list_interventions(session, classroom_id, status_filter)


@router.post(
    "/classrooms/{classroom_id}/interventions",
    response_model=InterventionDetailOut,
    summary="Create a new teacher intervention plan",
)
async def create_intervention(
    classroom_id: int,
    req: InterventionCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> InterventionDetailOut:
    verify_classroom_access(current_teacher, classroom_id)
    return await intervention_service.create_intervention(
        session, classroom_id, current_teacher.id, req
    )


@router.get(
    "/classrooms/{classroom_id}/interventions/{intervention_id}",
    response_model=InterventionDetailOut,
    summary="Get intervention detail including student assignments and baseline masteries",
)
async def get_intervention(
    classroom_id: int,
    intervention_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> InterventionDetailOut:
    verify_classroom_access(current_teacher, classroom_id)
    return await intervention_service.get_intervention_detail(session, classroom_id, intervention_id)


@router.post(
    "/classrooms/{classroom_id}/interventions/{intervention_id}/assign",
    response_model=InterventionDetailOut,
    summary="Assign selected students to an intervention",
)
async def assign_intervention(
    classroom_id: int,
    intervention_id: int,
    req: InterventionAssignRequest,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> InterventionDetailOut:
    verify_classroom_access(current_teacher, classroom_id)
    return await intervention_service.assign_intervention(
        session, classroom_id, intervention_id, req.student_ids
    )


@router.get(
    "/classrooms/{classroom_id}/interventions/{intervention_id}/outcomes",
    response_model=InterventionOutcomesResponse,
    summary="Measure pre/post intervention outcomes and misconception resolution",
)
async def get_intervention_outcomes(
    classroom_id: int,
    intervention_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_teacher: UserOut = Depends(require_teacher),
) -> InterventionOutcomesResponse:
    verify_classroom_access(current_teacher, classroom_id)
    return await intervention_service.get_intervention_outcomes(
        session, classroom_id, intervention_id
    )
