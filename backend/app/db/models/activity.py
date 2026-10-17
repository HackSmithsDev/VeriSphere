import enum
from datetime import UTC, date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ActivityCategory(str, enum.Enum):
    CERTIFICATION = "certification"
    COURSE = "course"
    EVENT = "event"
    INTERNSHIP = "internship"
    PROJECT = "project"
    CLUB = "club"
    VOLUNTEERING = "volunteering"
    LEADERSHIP = "leadership"
    COMPETITION = "competition"
    COMMUNITY_SERVICE = "community_service"
    OTHER = "other"


class ActivityStatus(str, enum.Enum):
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    NEEDS_REVISION = "needs_revision"


class StudentActivity(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profile.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[ActivityCategory] = mapped_column(
        Enum(ActivityCategory), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    achieved_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    proof_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    evidence_file_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("evidence_file.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ActivityStatus] = mapped_column(
        Enum(ActivityStatus),
        default=ActivityStatus.PENDING_VERIFICATION,
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, onupdate=_utc_now, nullable=False
    )

    student: Mapped["StudentProfile"] = relationship()
    reviewer: Mapped[Optional["User"]] = relationship()
    evidence_file: Mapped[Optional["EvidenceFile"]] = relationship()
