import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.practice import AIFallbackMeta, MasteryDelta


class TeachbackStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_id: str


class PipTurnOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str
    level: int = Field(..., ge=0, le=3)


class RubricOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key_points: list[str]


class TeachbackSessionStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    concept_id: str
    concept_name: str
    turn_count: int
    pip: PipTurnOut
    rubric: RubricOut
    finished: bool


class TeachbackTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(..., min_length=1, max_length=2000)


class TeachbackMisconceptionFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    statement: str


class TeachbackTurnFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float = Field(..., ge=0.0, le=1.0)
    covered: list[str]
    missing: list[str]
    misconceptions: list[TeachbackMisconceptionFeedback]


class TeachbackResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    final_score: float
    final_level: int
    mastery: MasteryDelta
    strengths: list[str]
    gaps: list[str]


class TeachbackTurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_index: int
    pip: PipTurnOut
    feedback: TeachbackTurnFeedback
    finished: bool
    result: TeachbackResultOut | None = None
    ai: AIFallbackMeta


class TeachbackTranscriptTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idx: int
    role: str
    content: str
    level: int | None = None
    created_at: datetime.datetime


class TeachbackDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    concept_id: str
    concept_name: str
    turn_count: int
    current_level: int
    finished: bool
    final_score: float | None = None
    turns: list[TeachbackTranscriptTurn]
