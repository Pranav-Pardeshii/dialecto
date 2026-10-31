import datetime

from pydantic import BaseModel, ConfigDict


class LearnerMasteryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_id: str
    concept_name: str
    chapter: str
    p_mastery: float
    p_effective: float
    attempts: int
    last_seen_at: datetime.datetime | None = None
    next_due_at: datetime.datetime | None = None
    status: str


class ActiveMisconceptionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    statement: str
    concept_id: str


class LearnerSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    overall_mastery: float
    weakest: list[str]
    due_count: int
    active_misconceptions: list[ActiveMisconceptionItem]
