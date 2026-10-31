import datetime
import enum
import uuid
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

# Cross-dialect JSON type: uses JSONB on Postgres, JSON elsewhere
JSONType = JSON().with_variant(JSONB, "postgresql")
UUIDType = UUID(as_uuid=True).with_variant(String(36), "sqlite")


# Enums
class UserRoleEnum(enum.StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"


class QuestionKindEnum(enum.StrEnum):
    MCQ = "mcq"


class QuestionSourceEnum(enum.StrEnum):
    SEED = "seed"
    LLM = "llm"


class SessionKindEnum(enum.StrEnum):
    DIAGNOSTIC = "diagnostic"
    PRACTICE = "practice"
    REVIEW = "review"
    TEACHBACK = "teachback"


class SessionStatusEnum(enum.StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MisconceptionSourceEnum(enum.StrEnum):
    DISTRACTOR = "distractor"
    LLM_REASONING = "llm_reasoning"
    TEACHBACK = "teachback"


class TeachbackRoleEnum(enum.StrEnum):
    PIP = "pip"
    LEARNER = "learner"


class LLMCallStatusEnum(enum.StrEnum):
    OK = "ok"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    INVALID_JSON = "invalid_json"
    ERROR = "error"


# Models
class Classroom(Base):
    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="classroom")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRoleEnum] = mapped_column(
        Enum(UserRoleEnum, name="user_role_enum", native_enum=False),
        nullable=False,
        default=UserRoleEnum.STUDENT,
    )
    classroom_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True
    )
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    classroom: Mapped[Optional["Classroom"]] = relationship(back_populates="users")
    masteries: Mapped[list["Mastery"]] = relationship(back_populates="user")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # slug
    chapter: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lesson_md: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    p_l0: Mapped[float] = mapped_column(Float, default=0.30, nullable=False)
    p_t: Mapped[float] = mapped_column(Float, default=0.15, nullable=False)
    p_s: Mapped[float] = mapped_column(Float, default=0.10, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        CheckConstraint("p_l0 >= 0.0 AND p_l0 <= 1.0", name="chk_concept_p_l0"),
        CheckConstraint("p_t >= 0.0 AND p_t <= 1.0", name="chk_concept_p_t"),
        CheckConstraint("p_s >= 0.0 AND p_s <= 1.0", name="chk_concept_p_s"),
    )

    questions: Mapped[list["Question"]] = relationship(back_populates="concept")
    misconceptions: Mapped[list["Misconception"]] = relationship(back_populates="concept")


class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"

    concept_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (
        CheckConstraint("concept_id <> prerequisite_id", name="chk_no_self_prereq"),
    )


class Misconception(Base):
    __tablename__ = "misconceptions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # slug
    concept_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    correction: Mapped[str] = mapped_column(Text, nullable=False)

    concept: Mapped["Concept"] = relationship(back_populates="misconceptions")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    concept_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[QuestionKindEnum] = mapped_column(
        Enum(QuestionKindEnum, name="question_kind_enum", native_enum=False),
        default=QuestionKindEnum.MCQ,
        nullable=False,
    )
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False)
    correct_key: Mapped[str] = mapped_column(String(10), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty_bucket: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)
    difficulty_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    n_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[QuestionSourceEnum] = mapped_column(
        Enum(QuestionSourceEnum, name="question_source_enum", native_enum=False),
        default=QuestionSourceEnum.SEED,
        nullable=False,
    )

    concept: Mapped["Concept"] = relationship(back_populates="questions")

    __table_args__ = (
        Index("ix_questions_concept_verified", "concept_id", "verified", "difficulty_rating"),
    )


class Mastery(Base):
    __tablename__ = "mastery"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    p_mastery: Mapped[float] = mapped_column(Float, default=0.30, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ease: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_due_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    user: Mapped["User"] = relationship(back_populates="masteries")

    __table_args__ = (
        CheckConstraint("p_mastery >= 0.0 AND p_mastery <= 1.0", name="chk_mastery_p_val"),
        Index("ix_mastery_concept", "concept_id"),
        Index("ix_mastery_user_due", "user_id", "next_due_at"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[SessionKindEnum] = mapped_column(
        Enum(SessionKindEnum, name="session_kind_enum", native_enum=False),
        nullable=False,
    )
    status: Mapped[SessionStatusEnum] = mapped_column(
        Enum(SessionStatusEnum, name="session_status_enum", native_enum=False),
        default=SessionStatusEnum.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC), nullable=False
    )
    ended_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="sessions")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="session")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    client_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, unique=True, nullable=False, default=uuid.uuid4
    )
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False
    )
    concept_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("concepts.id", ondelete="RESTRICT"), nullable=False
    )
    selected_key: Mapped[str] = mapped_column(String(10), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasoning_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mastery_before: Mapped[float] = mapped_column(Float, nullable=False)
    mastery_after: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC), nullable=False
    )

    session: Mapped["Session"] = relationship(back_populates="attempts")

    __table_args__ = (
        Index("ix_attempts_user_created", "user_id", "created_at"),
        Index("ix_attempts_concept", "concept_id"),
    )


class DetectedMisconception(Base):
    __tablename__ = "detected_misconceptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    misconception_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("misconceptions.id", ondelete="CASCADE"), nullable=False
    )
    attempt_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("attempts.id", ondelete="CASCADE"), nullable=True
    )
    teachback_turn_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("teachback_turns.id", ondelete="CASCADE"), nullable=True
    )
    source: Mapped[MisconceptionSourceEnum] = mapped_column(
        Enum(MisconceptionSourceEnum, name="misconception_source_enum", native_enum=False),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC), nullable=False
    )
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_detected_misconceptions_user", "user_id", "resolved_at"),
        Index("ix_detected_misconceptions_misconception", "misconception_id"),
    )


class TeachbackSession(Base):
    __tablename__ = "teachback_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("concepts.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[SessionStatusEnum] = mapped_column(
        Enum(SessionStatusEnum, name="tb_session_status_enum", native_enum=False),
        default=SessionStatusEnum.ACTIVE,
        nullable=False,
    )
    turn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    turns: Mapped[list["TeachbackTurn"]] = relationship(back_populates="teachback_session")


class TeachbackTurn(Base):
    __tablename__ = "teachback_turns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    teachback_session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teachback_sessions.id", ondelete="CASCADE"), nullable=False
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[TeachbackRoleEnum] = mapped_column(
        Enum(TeachbackRoleEnum, name="teachback_role_enum", native_enum=False),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    judge: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC), nullable=False
    )

    teachback_session: Mapped["TeachbackSession"] = relationship(back_populates="turns")

    __table_args__ = (
        UniqueConstraint("teachback_session_id", "idx", name="uq_teachback_session_idx"),
    )


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[LLMCallStatusEnum] = mapped_column(
        Enum(LLMCallStatusEnum, name="llm_call_status_enum", native_enum=False),
        default=LLMCallStatusEnum.OK,
        nullable=False,
    )
    error_class: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC), nullable=False
    )

    __table_args__ = (
        Index("ix_llm_calls_created", "created_at"),
        Index("ix_llm_calls_model_created", "model", "created_at"),
    )
