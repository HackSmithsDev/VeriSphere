"""Add expiring student account invitations."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0007_student_invitations"
down_revision = "0006_assistant_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "student_invitation" not in inspector.get_table_names():
        op.create_table(
            "student_invitation",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("first_name", sa.String(length=100), nullable=False),
            sa.Column("last_name", sa.String(length=100), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("accepted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["course_id"], ["course.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_student_invitation_email", "student_invitation", ["email"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "student_invitation" in inspector.get_table_names():
        op.drop_index("ix_student_invitation_email", table_name="student_invitation")
        op.drop_table("student_invitation")
