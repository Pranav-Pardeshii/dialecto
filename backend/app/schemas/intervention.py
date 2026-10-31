import datetime

from pydantic import BaseModel, Field


class AffectedStudentOut(BaseModel):
    id: int
    display_name: str
    baseline_mastery: float
    evidence_strength: str


class InterventionRecommendationOut(BaseModel):
    concept_id: str
    concept_name: str
    chapter: str
    title: str
    learning_gap: str
    target_misconception_id: str | None = None
    target_misconception_statement: str | None = None
    affected_student_count: int
    affected_students: list[AffectedStudentOut] = Field(default_factory=list)
    activity_type: str = "practice"
    recommended_remediation: str
    suggested_duration_mins: int = 15
    reason: str


class InterventionCreateRequest(BaseModel):
    concept_id: str
    title: str
    learning_gap: str
    target_misconception_id: str | None = None
    activity_type: str = "practice"
    recommended_remediation: str
    status: str = "draft"


class InterventionAssignRequest(BaseModel):
    student_ids: list[int]


class InterventionAssignmentOut(BaseModel):
    id: int
    intervention_id: int
    user_id: int
    student_name: str
    baseline_mastery: float
    post_mastery: float | None = None
    baseline_evidence_strength: str
    post_evidence_strength: str | None = None
    status: str
    assigned_at: datetime.datetime
    completed_at: datetime.datetime | None = None


class InterventionDetailOut(BaseModel):
    id: int
    teacher_id: int
    classroom_id: int
    concept_id: str
    concept_name: str
    title: str
    learning_gap: str
    target_misconception_id: str | None = None
    activity_type: str
    recommended_remediation: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    total_assigned: int
    completed_count: int
    assignments: list[InterventionAssignmentOut] = Field(default_factory=list)


class InterventionOutcomesResponse(BaseModel):
    intervention_id: int
    title: str
    concept_id: str
    concept_name: str
    status: str
    total_assigned: int
    completed_count: int
    completion_rate: float
    mean_baseline_mastery: float
    mean_post_mastery: float | None = None
    mean_mastery_gain: float | None = None
    misconceptions_resolved_count: int = 0
    sample_size_sufficient: bool = False
    outcome_summary: str
    assignments: list[InterventionAssignmentOut] = Field(default_factory=list)


class StudentInterventionItemOut(BaseModel):
    assignment_id: int
    intervention_id: int
    concept_id: str
    concept_name: str
    title: str
    learning_gap: str
    activity_type: str
    recommended_remediation: str
    status: str
    assigned_at: datetime.datetime
