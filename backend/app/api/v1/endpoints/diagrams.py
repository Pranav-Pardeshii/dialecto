from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db_session
from app.schemas.diagram import (
    DiagramAssessmentResponse,
    DiagramAssessmentSubmitRequest,
    VoiceCommandRequest,
    VoiceCommandResponse,
)
from app.schemas.user import UserOut
from app.services.diagram_assessment_service import diagram_assessment_service
from app.services.diagram_command_service import diagram_command_service

router = APIRouter(prefix="/diagrams", tags=["Interactive Biology Lab"])


@router.get(
    "",
    response_model=list[dict[str, Any]],
    summary="List all loaded interactive biological diagrams",
)
async def list_diagrams(
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    return diagram_command_service.list_diagrams()


@router.get(
    "/{diagram_id}",
    response_model=dict[str, Any],
    summary="Get detailed diagram manifest with structures, pathways, and licence",
)
async def get_diagram_manifest(
    diagram_id: str,
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> dict[str, Any]:
    manifest = diagram_command_service.get_manifest(diagram_id)
    if not manifest:
        raise NotFoundError(f"Diagram '{diagram_id}' not found.")
    return manifest


@router.post(
    "/{diagram_id}/commands",
    response_model=VoiceCommandResponse,
    summary="Interpret natural-language Wispr Flow voice or text command",
)
async def interpret_voice_command(
    diagram_id: str,
    req: VoiceCommandRequest,
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> VoiceCommandResponse:
    res = diagram_command_service.interpret_command(
        diagram_id=diagram_id,
        spoken_text=req.spoken_text,
        is_assessment_mode=req.is_assessment_mode,
        target_question_id=req.active_question_id,
    )
    return VoiceCommandResponse(
        action=res.action,
        target_structure_id=res.target_structure_id,
        target_structure_name=res.target_structure_name,
        pathway_id=res.pathway_id,
        view_direction=res.view_direction,
        zoom_level=res.zoom_level,
        message=res.message,
        clarification_options=res.clarification_options,
        confidence=res.confidence,
    )


@router.post(
    "/{diagram_id}/assessments",
    response_model=DiagramAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit diagram assessment answer with atomic BKT learner model update",
)
async def submit_diagram_assessment(
    diagram_id: str,
    req: DiagramAssessmentSubmitRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> DiagramAssessmentResponse:
    return await diagram_assessment_service.evaluate_and_persist(
        session=session,
        user_id=current_user.id,
        req=req,
    )

