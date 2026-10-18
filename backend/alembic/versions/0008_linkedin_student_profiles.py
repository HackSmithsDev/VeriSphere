"""Store consented LinkedIn profile details."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0008_linkedin_student_profiles"
down_revision = "0007_student_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in inspect(op.get_bind()).get_columns("student_profile")
    }
    if "linkedin_name" not in columns:
        op.add_column(
            "student_profile", sa.Column("linkedin_name", sa.String(255), nullable=True)
        )
    if "linkedin_picture_url" not in columns:
        op.add_column(
            "student_profile",
            sa.Column("linkedin_picture_url", sa.String(2048), nullable=True),
        )


def downgrade() -> None:
    columns = {
        column["name"]
        for column in inspect(op.get_bind()).get_columns("student_profile")
    }
    if "linkedin_picture_url" in columns:
        op.drop_column("student_profile", "linkedin_picture_url")
    if "linkedin_name" in columns:
        op.drop_column("student_profile", "linkedin_name")
