import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class QuestionOptionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    text: str


class QuestionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    concept_id: str
    stem: str
    options: list[QuestionOptionOut]
    difficulty_bucket: int


class PracticeNextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str = Field(default="adaptive", pattern="^(adaptive|review|concept)$")
    concept_id: str | None = None


class PracticeNextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: int
    question: QuestionOut
    selection_reason: str


class PracticeAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_attempt_id: uuid.UUID
    session_id: int
    question_id: str
    selected_key: str
    reasoning: str | None = Field(default=None, max_length=600)
    response_ms: int = Field(default=0, ge=0)


class MisconceptionFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    statement: str
    correction: str
    source: str
    confidence: float


class MasteryDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_id: str
    before: float
    after: float
    status: str


class AIFallbackMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    used: bool = False
    model: str | None = None
    fallback: bool = False


class PracticeAnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_correct: bool
    correct_key: str
    explanation: str
    mastery: MasteryDelta
    next_due_at: datetime.datetime | None = None
    misconception: MisconceptionFeedback | None = None
    ai: AIFallbackMeta
    newly_unlocked: list[str] = []
