# backend/app/db/models/academic.py
from typing import List
from sqlalchemy import String, Integer, ForeignKey, Text, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


teacher_course_assignment = Table(
    "teacher_course_assignment",
    Base.metadata,
    Column(
        "teacher_id",
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "course_id",
        Integer,
        ForeignKey("course.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Course(Base):
    """E.g., B.Tech Computer Science Engineering (AI & ML)"""
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    duration_years: Mapped[int] = mapped_column(Integer, default=4)

    subjects: Mapped[List["Subject"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    students: Mapped[List["StudentProfile"]] = relationship(back_populates="course")
    teachers: Mapped[List["User"]] = relationship(
        secondary=teacher_course_assignment, back_populates="assigned_courses"
    )


class Subject(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("course.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="subjects")
    chapters: Mapped[List["Chapter"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class Chapter(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id", ondelete="CASCADE"), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    subject: Mapped["Subject"] = relationship(back_populates="chapters")
    student_milestones: Mapped[List["StudentMilestone"]] = relationship(back_populates="chapter", cascade="all, delete-orphan")