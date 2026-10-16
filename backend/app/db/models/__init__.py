# backend/app/db/models/__init__.py
from app.db.models.user import User, UserRole, StudentProfile, TeacherProfile
from app.db.models.academic import Course, Subject, Chapter
from app.db.models.milestone import StudentMilestone, MilestoneStatus


__all__ = [
    "User",
    "UserRole",
    "StudentProfile",
    "TeacherProfile",
    "Course",
    "Subject",
    "Chapter",
    "StudentMilestone",
    "MilestoneStatus",
]