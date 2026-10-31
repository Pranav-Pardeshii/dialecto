import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewDueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_id: str
    name: str
    chapter: str
    p_effective: float = Field(..., ge=0.0, le=1.0)
    days_overdue: int = Field(..., ge=0)
    next_due_at: datetime.datetime | None = None
