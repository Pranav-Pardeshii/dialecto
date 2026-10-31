import datetime
from typing import Any

from pydantic import BaseModel, Field


class TimelineEventOut(BaseModel):
    event_type: str
    timestamp: datetime.datetime
    description: str
    is_correct: bool
    mastery_before: float
    mastery_after: float
    mastery_delta: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class MisconceptionStateOut(BaseModel):
    id: str
    statement: str
    correction: str
    detected_at: datetime.datetime
    resolved_at: datetime.datetime | None = None


class AssessmentBreakdownOut(BaseModel):
    practice_count: int = 0
    diagnostic_count: int = 0
    teachback_count: int = 0
    diagram_count: int = 0


class ExplainableConceptMasteryResponse(BaseModel):
    concept_id: str
    concept_name: str
    chapter: str
    p_mastery: float
    p_effective: float
    status: str
    evidence_strength: str
    evidence_score: float
    total_attempts: int
    correct_attempts: int
    accuracy_rate: float
    recent_trend: str
    last_seen_at: datetime.datetime | None = None
    next_due_at: datetime.datetime | None = None
    is_overdue: bool = False
    days_overdue: int = 0
    assessment_breakdown: AssessmentBreakdownOut
    active_misconceptions: list[MisconceptionStateOut] = Field(default_factory=list)
    resolved_misconceptions: list[MisconceptionStateOut] = Field(default_factory=list)
    unmet_prerequisites: list[str] = Field(default_factory=list)
    narrative: str
    timeline: list[TimelineEventOut] = Field(default_factory=list)

