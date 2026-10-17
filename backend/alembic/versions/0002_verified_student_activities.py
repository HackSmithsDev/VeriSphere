"""Add verified student activities and portfolio sharing."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0002_verified_activities"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


activity_category = sa.Enum(
    "CERTIFICATION",
    "COURSE",
    "EVENT",
    "INTERNSHIP",
    "PROJECT",
    "CLUB",
    "VOLUNTEERING",
    "LEADERSHIP",
    "COMPETITION",
    "COMMUNITY_SERVICE",
    "OTHER",
    name="activitycategory",
)
activity_status = sa.Enum(
    "PENDING_VERIFICATION",
    "VERIFIED",
    "NEEDS_REVISION",
    name="activitystatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    activity_category.create(bind, checkfirst=True)
    activity_status.create(bind, checkfirst=True)
    inspector = inspect(bind)
    profile_columns = {
        column["name"] for column in inspector.get_columns("student_profile")
    }
    if "portfolio_share_token" not in profile_columns:
        op.add_column(
            "student_profile",
            sa.Column("portfolio_share_token", sa.String(length=64), nullable=True),
        )
        op.create_index(
            "ix_student_profile_portfolio_share_token",
            "student_profile",
            ["portfolio_share_token"],
            unique=True,
        )
    if "student_activity" not in inspector.get_table_names():
        op.create_table(
            "student_activity",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("category", activity_category, nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("issuer", sa.String(length=255), nullable=True),
            sa.Column("achieved_on", sa.Date(), nullable=True),
            sa.Column("proof_url", sa.String(length=2048), nullable=False),
            sa.Column("status", activity_status, nullable=False),
            sa.Column("reviewer_id", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("review_feedback", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["reviewer_id"], ["user.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["student_id"], ["student_profile.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_student_activity_id", "student_activity", ["id"])
        op.create_index(
            "ix_student_activity_student_id", "student_activity", ["student_id"]
        )
        op.create_index(
            "ix_student_activity_category", "student_activity", ["category"]
        )
        op.create_index(
            "ix_student_activity_status", "student_activity", ["status"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "student_activity" in inspector.get_table_names():
        op.drop_table("student_activity")
    profile_columns = {
        column["name"] for column in inspect(bind).get_columns("student_profile")
    }
    if "portfolio_share_token" in profile_columns:
        profile_indexes = {
            index["name"] for index in inspect(bind).get_indexes("student_profile")
        }
        if "ix_student_profile_portfolio_share_token" in profile_indexes:
            op.drop_index(
                "ix_student_profile_portfolio_share_token",
                table_name="student_profile",
            )
        op.drop_column("student_profile", "portfolio_share_token")
    activity_status.drop(bind, checkfirst=True)
    activity_category.drop(bind, checkfirst=True)
