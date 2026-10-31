from typing import Any

from pydantic import BaseModel, Field


class QuestionOptionSchema(BaseModel):
    key: str
    text: str
    misconception_id: str | None = None


class QuestionGenerateRequest(BaseModel):
    concept_id: str
    chapter_id: str | None = None
    subconcept: str | None = None
    difficulty_bucket: int = Field(default=2, ge=1, le=3)
    kind: str = Field(default="mcq")
    count: int = Field(default=3, ge=1, le=10)
    target_misconception_id: str | None = None
    cognitive_skill: str | None = None
    learning_objective: str | None = None


class QuestionCreateRequest(BaseModel):
    concept_id: str
    kind: str = "mcq"
    stem: str
    options: list[QuestionOptionSchema] = Field(default_factory=list)
    correct_key: str
    explanation: str
    difficulty_bucket: int = Field(default=2, ge=1, le=3)
    learning_objective: str | None = None
    cognitive_skill: str | None = None
    curriculum_ref: str | None = None
    distractor_explanations: dict[str, str] | None = None


class QuestionUpdateRequest(BaseModel):
    stem: str | None = None
    kind: str | None = None
    options: list[QuestionOptionSchema] | None = None
    correct_key: str | None = None
    explanation: str | None = None
    difficulty_bucket: int | None = Field(default=None, ge=1, le=3)
    learning_objective: str | None = None
    cognitive_skill: str | None = None
    curriculum_ref: str | None = None
    distractor_explanations: dict[str, str] | None = None


class QuestionReviewActionRequest(BaseModel):
    action: str = Field(description="'approve' or 'reject'")
    rejection_reason: str | None = None


class QuestionAuthoringOut(BaseModel):
    id: str
    concept_id: str
    kind: str
    stem: str
    options: list[dict[str, Any]]
    correct_key: str
    explanation: str
    difficulty_bucket: int
    difficulty_rating: float
    n_attempts: int
    verified: bool
    source: str
    review_status: str
    version: int
    parent_id: str | None = None
    author_id: int | None = None
    learning_objective: str | None = None
    cognitive_skill: str | None = None
    curriculum_ref: str | None = None
    generation_model: str | None = None
    distractor_explanations: dict[str, Any] | None = None
    rejection_reason: str | None = None


class QuestionAuthoringListResponse(BaseModel):
    questions: list[QuestionAuthoringOut]
    total: int


class GeneratedQuestionBatchResponse(BaseModel):
    generated: list[QuestionAuthoringOut]
    validation_passed: int
    validation_failed: int
    errors: list[str] = Field(default_factory=list)
