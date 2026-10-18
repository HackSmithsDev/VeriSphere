"""Store anonymous assistant helpfulness ratings."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0006_assistant_feedback"
down_revision = "0005_teacher_course_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "assistant_feedback" not in inspector.get_table_names():
        op.create_table(
            "assistant_feedback",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("helpful", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        )
        op.create_index(
            "ix_assistant_feedback_user_id", "assistant_feedback", ["user_id"]
        )
        op.create_index(
            "ix_assistant_feedback_provider", "assistant_feedback", ["provider"]
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "assistant_feedback" in inspector.get_table_names():
        op.drop_index("ix_assistant_feedback_provider", table_name="assistant_feedback")
        op.drop_index("ix_assistant_feedback_user_id", table_name="assistant_feedback")
        op.drop_table("assistant_feedback")
