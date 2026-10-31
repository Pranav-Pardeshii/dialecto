"""002_authoring_diagrams

Revision ID: 002_authoring_diagrams
Revises: 001_initial_schema
Create Date: 2026-10-31 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "002_authoring_diagrams"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONType = sa.JSON().with_variant(JSONB, "postgresql")
UUIDType = UUID(as_uuid=True).with_variant(sa.String(36), "sqlite")


def upgrade() -> None:
    # 1. Extend questions table with authoring & versioning columns
    op.add_column(
        "questions",
        sa.Column(
            "review_status",
            sa.String(50),
            nullable=False,
            server_default="approved",
        ),
    )
    op.add_column(
        "questions",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "questions",
        sa.Column(
            "parent_id",
            sa.String(100),
            sa.ForeignKey("questions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "questions",
        sa.Column(
            "author_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "questions",
        sa.Column("learning_objective", sa.Text(), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("cognitive_skill", sa.String(50), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("curriculum_ref", sa.String(255), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("generation_model", sa.String(100), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("distractor_explanations", JSONType, nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_questions_review_status",
        "questions",
        ["review_status", "verified"],
    )

    # 2. Interventions table
    op.create_table(
        "interventions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "teacher_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "classroom_id",
            sa.BigInteger(),
            sa.ForeignKey("classrooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("learning_gap", sa.Text(), nullable=False),
        sa.Column(
            "target_misconception_id",
            sa.String(100),
            sa.ForeignKey("misconceptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "activity_type",
            sa.String(50),
            nullable=False,
            server_default="practice",
        ),
        sa.Column("recommended_remediation", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_interventions_classroom",
        "interventions",
        ["classroom_id", "status"],
    )
    op.create_index(
        "ix_interventions_concept",
        "interventions",
        ["concept_id"],
    )

    # 3. Intervention Assignments table
    op.create_table(
        "intervention_assignments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "intervention_id",
            sa.BigInteger(),
            sa.ForeignKey("interventions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("baseline_mastery", sa.Float(), nullable=False),
        sa.Column("post_mastery", sa.Float(), nullable=True),
        sa.Column("baseline_evidence_strength", sa.String(50), nullable=False, server_default="low"),
        sa.Column("post_evidence_strength", sa.String(50), nullable=True),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="assigned",
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_intervention_assignments_user",
        "intervention_assignments",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_intervention_assignments_unique",
        "intervention_assignments",
        ["intervention_id", "user_id"],
        unique=True,
    )

    # 4. Diagram Assessments table
    op.create_table(
        "diagram_assessments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "client_attempt_id",
            UUIDType,
            unique=True,
            nullable=False,
        ),
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
        sa.Column("diagram_id", sa.String(100), nullable=False),
        sa.Column("assessment_type", sa.String(50), nullable=False),
        sa.Column("target_structure_id", sa.String(100), nullable=True),
        sa.Column("user_response", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column(
            "detected_misconception_id",
            sa.String(100),
            sa.ForeignKey("misconceptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mastery_before", sa.Float(), nullable=False),
        sa.Column("mastery_after", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_diagram_assessments_user",
        "diagram_assessments",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_diagram_assessments_diagram",
        "diagram_assessments",
        ["diagram_id", "concept_id"],
    )


def downgrade() -> None:
    op.drop_table("diagram_assessments")
    op.drop_table("intervention_assignments")
    op.drop_table("interventions")
    op.drop_index("ix_questions_review_status", table_name="questions")
    op.drop_column("questions", "rejection_reason")
    op.drop_column("questions", "distractor_explanations")
    op.drop_column("questions", "generation_model")
    op.drop_column("questions", "curriculum_ref")
    op.drop_column("questions", "cognitive_skill")
    op.drop_column("questions", "learning_objective")
    op.drop_column("questions", "author_id")
    op.drop_column("questions", "parent_id")
    op.drop_column("questions", "version")
    op.drop_column("questions", "review_status")
