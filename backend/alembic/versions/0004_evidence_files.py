"""Add private evidence file storage and record links."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0004_evidence_files"
down_revision = "0003_academic_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "evidence_file" not in tables:
        op.create_table(
            "evidence_file",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("storage_name", sa.String(length=64), nullable=False, unique=True),
            sa.Column("original_name", sa.String(length=255), nullable=False),
            sa.Column("media_type", sa.String(length=100), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["student_id"], ["student_profile.id"], ondelete="CASCADE"
            ),
        )
        op.create_index(
            "ix_evidence_file_student_id", "evidence_file", ["student_id"]
        )

    activity_columns = {
        column["name"] for column in inspect(bind).get_columns("student_activity")
    }
    if "evidence_file_id" not in activity_columns:
        op.add_column(
            "student_activity",
            sa.Column("evidence_file_id", sa.String(length=36), nullable=True),
        )
        with op.batch_alter_table("student_activity") as batch_op:
            batch_op.create_foreign_key(
                "fk_student_activity_evidence_file",
                "evidence_file",
                ["evidence_file_id"],
                ["id"],
                ondelete="SET NULL",
            )

    milestone_columns = {
        column["name"] for column in inspect(bind).get_columns("student_milestone")
    }
    if "evidence_file_id" not in milestone_columns:
        op.add_column(
            "student_milestone",
            sa.Column("evidence_file_id", sa.String(length=36), nullable=True),
        )
        with op.batch_alter_table("student_milestone") as batch_op:
            batch_op.create_foreign_key(
                "fk_student_milestone_evidence_file",
                "evidence_file",
                ["evidence_file_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "student_milestone" in tables:
        columns = {
            column["name"]
            for column in inspect(bind).get_columns("student_milestone")
        }
        if "evidence_file_id" in columns:
            with op.batch_alter_table("student_milestone") as batch_op:
                batch_op.drop_column("evidence_file_id")
    if "student_activity" in tables:
        columns = {
            column["name"] for column in inspect(bind).get_columns("student_activity")
        }
        if "evidence_file_id" in columns:
            with op.batch_alter_table("student_activity") as batch_op:
                batch_op.drop_column("evidence_file_id")
    if "evidence_file" in tables:
        op.drop_table("evidence_file")
