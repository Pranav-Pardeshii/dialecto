from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.schemas.diagnostic import (
    DiagnosticAnswerRequest,
    DiagnosticAnswerResponse,
    DiagnosticResultResponse,
    DiagnosticStartResponse,
)
from app.schemas.user import UserOut
from app.services.diagnostic_service import diagnostic_service

router = APIRouter(prefix="/diagnostic", tags=["Diagnostic"])


@router.post("/sessions", response_model=DiagnosticStartResponse)
async def start_diagnostic(
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> DiagnosticStartResponse:
    """Start an adaptive 15-question diagnostic assessment."""
    return await diagnostic_service.start_session(session, current_user.id)


@router.post("/sessions/{session_id}/answers", response_model=DiagnosticAnswerResponse)
async def submit_diagnostic_answer(
    session_id: int,
    req: DiagnosticAnswerRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> DiagnosticAnswerResponse:
    """Submit diagnostic answer and progress to the next calibrated question."""
    return await diagnostic_service.submit_answer(session, current_user.id, session_id, req)


@router.get("/sessions/{session_id}/result", response_model=DiagnosticResultResponse)
async def get_diagnostic_result(
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> DiagnosticResultResponse:
    """Retrieve full mastery profile resulting from completed diagnostic session."""
    return await diagnostic_service.get_session_result(session, session_id, current_user.id)
