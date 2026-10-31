import datetime

from pydantic import BaseModel, ConfigDict, Field


class HeatmapConceptOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    chapter: str


class HeatmapStudentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    display_name: str


class HeatmapCellOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: int
    concept_id: str
    p_effective: float = Field(..., ge=0.0, le=1.0)


class TeacherHeatmapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    classroom_id: int
    classroom_name: str
    concepts: list[HeatmapConceptOut]
    students: list[HeatmapStudentOut]
    cells: list[HeatmapCellOut]


class CurriculumGapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_id: str
    name: str
    chapter: str
    mean_mastery: float = Field(..., ge=0.0, le=1.0)
    pct_below_50: float = Field(..., ge=0.0, le=100.0)
    n_students: int = Field(..., ge=0)


class MisconceptionPrevalenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    misconception_id: str
    statement: str
    concept_id: str
    concept_name: str
    n_students: int = Field(..., ge=0)


class AtRiskStudentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: int
    display_name: str
    mean_mastery: float = Field(..., ge=0.0, le=1.0)
    overdue_count: int = Field(..., ge=0)
    active_misconceptions_count: int = Field(..., ge=0)


class StudentAttemptBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    question_id: str
    concept_id: str
    is_correct: bool
    created_at: datetime.datetime


class StudentMasteryDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_id: str
    concept_name: str
    p_mastery: float
    p_effective: float
    status: str
    next_due_at: datetime.datetime | None = None


class StudentMisconceptionDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    misconception_id: str
    statement: str
    source: str
    confidence: float
    detected_at: datetime.datetime


class StudentDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: int
    display_name: str
    overall_mastery: float
    masteries: list[StudentMasteryDetail]
    active_misconceptions: list[StudentMisconceptionDetail]
    recent_attempts: list[StudentAttemptBrief]
