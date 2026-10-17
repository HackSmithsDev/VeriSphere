"""Add attendance and assessment records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0003_academic_records"
down_revision = "0002_verified_activities"
branch_labels = None
depends_on = None


attendance_status = sa.Enum(
    "PRESENT", "ABSENT", "EXCUSED", name="attendancestatus"
)


def upgrade() -> None:
    bind = op.get_bind()
    attendance_status.create(bind, checkfirst=True)
    tables = set(inspect(bind).get_table_names())
    if "attendance_record" not in tables:
        op.create_table(
            "attendance_record",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.Column("recorded_by", sa.Integer(), nullable=False),
            sa.Column("attendance_date", sa.Date(), nullable=False),
            sa.Column("status", attendance_status, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["student_id"], ["student_profile.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["subject_id"], ["subject.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["recorded_by"], ["user.id"], ondelete="RESTRICT"
            ),
            sa.UniqueConstraint(
                "student_id",
                "subject_id",
                "attendance_date",
                name="uq_attendance_session",
            ),
        )
        op.create_index("ix_attendance_record_id", "attendance_record", ["id"])
    if "assessment_mark" not in tables:
        op.create_table(
            "assessment_mark",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.Column("recorded_by", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("maximum_score", sa.Float(), nullable=False),
            sa.Column("assessment_date", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["student_id"], ["student_profile.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["subject_id"], ["subject.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["recorded_by"], ["user.id"], ondelete="RESTRICT"
            ),
        )
        op.create_index("ix_assessment_mark_id", "assessment_mark", ["id"])


def downgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "assessment_mark" in tables:
        op.drop_table("assessment_mark")
    if "attendance_record" in tables:
        op.drop_table("attendance_record")
    attendance_status.drop(op.get_bind(), checkfirst=True)
