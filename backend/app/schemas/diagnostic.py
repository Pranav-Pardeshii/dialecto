import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.practice import QuestionOut


class DiagnosticProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answered: int
    total: int = 15


class DiagnosticStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: int
    question: QuestionOut
    progress: DiagnosticProgress


class DiagnosticAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_attempt_id: uuid.UUID
    question_id: str
    selected_key: str
    reasoning: str | None = Field(default=None, max_length=600)
    response_ms: int = Field(default=0, ge=0)


class DiagnosticConceptResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_id: str
    concept_name: str
    p_mastery: float
    status: str


class DiagnosticResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mastery: list[DiagnosticConceptResult]
    weakest: list[str]
    recommended_next: str


class DiagnosticAnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_correct: bool
    next_question: QuestionOut | None = None
    progress: DiagnosticProgress
    result: DiagnosticResultResponse | None = None
