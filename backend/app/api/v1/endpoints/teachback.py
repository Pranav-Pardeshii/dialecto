from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.schemas.teachback import (
    TeachbackDetailResponse,
    TeachbackSessionStartResponse,
    TeachbackStartRequest,
    TeachbackTurnRequest,
    TeachbackTurnResponse,
)
from app.schemas.user import UserOut
from app.services.teachback_service import teachback_service

router = APIRouter(prefix="/teachback", tags=["Teach-Back Mode with Pip"])


@router.post("/sessions", response_model=TeachbackSessionStartResponse)
async def start_teachback_session(
    req: TeachbackStartRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> TeachbackSessionStartResponse:
    """Initialize a Teach-Back dialogue session with Pip, returning Pip's opening question and the concept rubric."""
    return await teachback_service.start_session(session, current_user.id, req.concept_id)


@router.post("/sessions/{session_id}/turns", response_model=TeachbackTurnResponse)
async def submit_teachback_turn(
    session_id: int,
    req: TeachbackTurnRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> TeachbackTurnResponse:
    """Submit a teaching explanation to Pip. Returns Pip's dialogue, rubric coverage feedback, and soft evidence delta."""
    return await teachback_service.submit_turn(session, current_user.id, session_id, req)


@router.get("/sessions/{session_id}", response_model=TeachbackDetailResponse)
async def get_teachback_session(
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserOut = Depends(get_current_user),
) -> TeachbackDetailResponse:
    """Retrieve full transcript and state of a Teach-Back dialogue session."""
    return await teachback_service.get_session_detail(session, current_user.id, session_id)

