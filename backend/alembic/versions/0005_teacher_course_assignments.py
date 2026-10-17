"""Scope faculty access to assigned courses."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0005_teacher_course_assignments"
down_revision = "0004_evidence_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "teacher_course_assignment" not in inspect(op.get_bind()).get_table_names():
        op.create_table(
            "teacher_course_assignment",
            sa.Column("teacher_id", sa.Integer(), nullable=False),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["teacher_id"], ["user.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["course_id"], ["course.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("teacher_id", "course_id"),
        )


def downgrade() -> None:
    if "teacher_course_assignment" in inspect(op.get_bind()).get_table_names():
        op.drop_table("teacher_course_assignment")
