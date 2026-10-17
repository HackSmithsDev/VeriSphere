# backend/app/db/models/user.py
import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, ForeignKey, Boolean, Enum, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"

class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Polymorphic profiles links
    student_profile: Mapped[Optional["StudentProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    teacher_profile: Mapped[Optional["TeacherProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class StudentProfile(Base):
    """The dynamic data intake platform. Feeds raw parameters to the AI Resume Engine."""
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), unique=True, nullable=False)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("course.id"), nullable=False)
    
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_semester: Mapped[int] = mapped_column(Integer, default=1)
    
    biography: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    career_preferences: Mapped[dict] = mapped_column(JSON, default=dict)   # Targeted tech roles & industry tracks
    verified_hard_points: Mapped[dict] = mapped_column(JSON, default=dict)  # AI-compiled structured achievements
    portfolio_share_token: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="student_profile")
    course: Mapped["Course"] = relationship(back_populates="students")
    milestones: Mapped[List["StudentMilestone"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class TeacherProfile(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship(back_populates="teacher_profile")