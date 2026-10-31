"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-31 15:28:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONType = sa.JSON().with_variant(JSONB, "postgresql")
UUIDType = UUID(as_uuid=True).with_variant(sa.String(36), "sqlite")


def upgrade() -> None:
    # Classrooms
    op.create_table(
        "classrooms",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="student"),
        sa.Column(
            "classroom_id",
            sa.BigInteger(),
            sa.ForeignKey("classrooms.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Concepts
    op.create_table(
        "concepts",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("chapter", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("lesson_md", sa.Text(), nullable=False),
        sa.Column("key_points", JSONType, nullable=False),
        sa.Column("p_l0", sa.Float(), nullable=False, server_default="0.30"),
        sa.Column("p_t", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("p_s", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("p_l0 >= 0.0 AND p_l0 <= 1.0", name="chk_concept_p_l0"),
        sa.CheckConstraint("p_t >= 0.0 AND p_t <= 1.0", name="chk_concept_p_t"),
        sa.CheckConstraint("p_s >= 0.0 AND p_s <= 1.0", name="chk_concept_p_s"),
    )

    # Concept Prerequisites
    op.create_table(
        "concept_prerequisites",
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "prerequisite_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.CheckConstraint("concept_id <> prerequisite_id", name="chk_no_self_prereq"),
    )

    # Misconceptions
    op.create_table(
        "misconceptions",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("correction", sa.Text(), nullable=False),
    )

    # Questions
    op.create_table(
        "questions",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(50), nullable=False, server_default="mcq"),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("options", JSONType, nullable=False),
        sa.Column("correct_key", sa.String(10), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("difficulty_bucket", sa.SmallInteger(), nullable=False, server_default="2"),
        sa.Column("difficulty_rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("n_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source", sa.String(50), nullable=False, server_default="seed"),
    )
    op.create_index(
        "ix_questions_concept_verified",
        "questions",
        ["concept_id", "verified", "difficulty_rating"],
    )

    # Mastery
    op.create_table(
        "mastery",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("p_mastery", sa.Float(), nullable=False, server_default="0.30"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ease", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("p_mastery >= 0.0 AND p_mastery <= 1.0", name="chk_mastery_p_val"),
    )
    op.create_index("ix_mastery_concept", "mastery", ["concept_id"])
    op.create_index("ix_mastery_user_due", "mastery", ["user_id", "next_due_at"])

    # Sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Attempts
    op.create_table(
        "attempts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("client_attempt_id", UUIDType, nullable=False, unique=True),
        sa.Column(
            "session_id",
            sa.BigInteger(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.String(100),
            sa.ForeignKey("questions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("selected_key", sa.String(10), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("reasoning_text", sa.Text(), nullable=True),
        sa.Column("response_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mastery_before", sa.Float(), nullable=False),
        sa.Column("mastery_after", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_attempts_user_created", "attempts", ["user_id", "created_at"])
    op.create_index("ix_attempts_concept", "attempts", ["concept_id"])

    # Teachback Sessions
    op.create_table(
        "teachback_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.BigInteger(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("final_level", sa.SmallInteger(), nullable=True),
    )

    # Teachback Turns
    op.create_table(
        "teachback_turns",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "teachback_session_id",
            sa.BigInteger(),
            sa.ForeignKey("teachback_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("judge", JSONType, nullable=True),
        sa.Column("level", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("teachback_session_id", "idx", name="uq_teachback_session_idx"),
    )

    # Detected Misconceptions
    op.create_table(
        "detected_misconceptions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "misconception_id",
            sa.String(100),
            sa.ForeignKey("misconceptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "attempt_id",
            sa.BigInteger(),
            sa.ForeignKey("attempts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "teachback_turn_id",
            sa.BigInteger(),
            sa.ForeignKey("teachback_turns.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_detected_misconceptions_user", "detected_misconceptions", ["user_id", "resolved_at"]
    )
    op.create_index(
        "ix_detected_misconceptions_misconception", "detected_misconceptions", ["misconception_id"]
    )

    # Observability: LLM Calls
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="ok"),
        sa.Column("error_class", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_llm_calls_created", "llm_calls", ["created_at"])
    op.create_index("ix_llm_calls_model_created", "llm_calls", ["model", "created_at"])


def downgrade() -> None:
    op.drop_table("llm_calls")
    op.drop_table("detected_misconceptions")
    op.drop_table("teachback_turns")
    op.drop_table("teachback_sessions")
    op.drop_table("attempts")
    op.drop_table("sessions")
    op.drop_table("mastery")
    op.drop_table("questions")
    op.drop_table("misconceptions")
    op.drop_table("concept_prerequisites")
    op.drop_table("concepts")
    op.drop_table("users")
    op.drop_table("classrooms")
