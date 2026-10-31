from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import ForbiddenError
from app.db.session import get_db_session
from app.schemas.teacher import (
    AtRiskStudentItem,
    CurriculumGapItem,
    MisconceptionPrevalenceItem,
    StudentDetailResponse,
    TeacherHeatmapResponse,
)
from app.schemas.user import UserOut, UserRole
from app.services.teacher_service import teacher_service

router = APIRouter(prefix="/teacher", tags=["Teacher Analytics"])


def require_teacher(current_user: UserOut = Depends(get_current_user)) -> UserOut:
    if current_user.role != UserRole.TEACHER:
        raise ForbiddenError("Teacher privileges required to access classroom analytics")
    return current_user


@router.get("/classrooms/{classroom_id}/heatmap", response_model=TeacherHeatmapResponse)
async def get_classroom_heatmap(
    classroom_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: UserOut = Depends(require_teacher),
) -> TeacherHeatmapResponse:
    """Retrieve full 30x20 student-concept effective mastery matrix."""
    return await teacher_service.get_heatmap(session, classroom_id)


@router.get("/classrooms/{classroom_id}/gaps", response_model=list[CurriculumGapItem])
async def get_classroom_gaps(
    classroom_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: UserOut = Depends(require_teacher),
) -> list[CurriculumGapItem]:
    """Retrieve concepts ranked by classroom failure rate and average mastery."""
    return await teacher_service.get_curriculum_gaps(session, classroom_id)


@router.get(
    "/classrooms/{classroom_id}/misconceptions", response_model=list[MisconceptionPrevalenceItem]
)
async def get_classroom_misconceptions(
    classroom_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: UserOut = Depends(require_teacher),
) -> list[MisconceptionPrevalenceItem]:
    """Retrieve classroom misconceptions sorted by prevalence across students."""
    return await teacher_service.get_misconception_prevalence(session, classroom_id)


@router.get("/classrooms/{classroom_id}/at-risk", response_model=list[AtRiskStudentItem])
async def get_at_risk_students(
    classroom_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: UserOut = Depends(require_teacher),
) -> list[AtRiskStudentItem]:
    """Retrieve list of students at risk due to critical misconceptions or low mastery."""
    return await teacher_service.get_at_risk_students(session, classroom_id)


@router.get(
    "/classrooms/{classroom_id}/students/{student_id}", response_model=StudentDetailResponse
)
async def get_student_drilldown(
    classroom_id: int,
    student_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: UserOut = Depends(require_teacher),
) -> StudentDetailResponse:
    """Retrieve deep dive into a student's concept masteries and active misconceptions."""
    return await teacher_service.get_student_detail(session, classroom_id, student_id)
