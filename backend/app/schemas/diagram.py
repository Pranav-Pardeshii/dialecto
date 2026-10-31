import uuid
from typing import Any

from pydantic import BaseModel, Field


class VoiceCommandRequest(BaseModel):
    diagram_id: str
    spoken_text: str
    is_assessment_mode: bool = False
    active_question_id: str | None = None


class VoiceCommandResponse(BaseModel):
    action: str
    target_structure_id: str | None = None
    target_structure_name: str | None = None
    pathway_id: str | None = None
    view_direction: str | None = None
    zoom_level: float | None = None
    message: str
    clarification_options: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class DiagramAssessmentSubmitRequest(BaseModel):
    client_attempt_id: uuid.UUID
    session_id: int | None = None
    diagram_id: str
    question_id: str
    assessment_type: str
    selected_structure_id: str | None = None
    selected_sequence: list[str] | None = None
    explanation_text: str | None = None


class DiagramAssessmentResponse(BaseModel):
    is_correct: bool
    score: float
    feedback: str
    target_structure_id: str | None = None
    target_sequence: list[str] | None = None
    mastery: dict[str, Any]
    detected_misconception: dict[str, Any] | None = None
    is_idempotent_replay: bool = False

