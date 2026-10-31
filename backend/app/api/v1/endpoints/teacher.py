from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_teacher, verify_classroom_access
from app.db.session import get_db_session
from app.schemas.teacher import (
    AtRiskStudentItem,
    CurriculumGapItem,
    MisconceptionPrevalenceItem,
    StudentDetailResponse,
    TeacherHeatmapResponse,
)
from app.schemas.user import UserOut
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
