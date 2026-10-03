# backend/app/db/models/milestone.py
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, ForeignKey, Enum, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class MilestoneStatus(str, enum.Enum):
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"

class StudentMilestone(Base):
    """Tracks continuous assessment data submissions & human-in-the-loop teacher signs-offs."""
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("student_profile.id", ondelete="CASCADE"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapter.id", ondelete="CASCADE"), nullable=False)
    
    status: Mapped[MilestoneStatus] = mapped_column(Enum(MilestoneStatus), default=MilestoneStatus.LOCKED, nullable=False)
    submission_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Student URLs, repo links, text verification proof
    teacher_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["StudentProfile"] = relationship(back_populates="milestones")
    chapter: Mapped["Chapter"] = relationship(back_populates="student_milestones")