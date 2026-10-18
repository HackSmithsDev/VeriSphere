# backend/app/db/models/__init__.py
from app.db.models.user import User, UserRole, StudentProfile, TeacherProfile
from app.db.models.academic import Course, Subject, Chapter
from app.db.models.milestone import StudentMilestone, MilestoneStatus
from app.db.models.activity import ActivityCategory, ActivityStatus, StudentActivity
from app.db.models.records import (
    AssessmentMark,
    AttendanceRecord,
    AttendanceStatus,
    EvidenceFile,
)
from app.db.models.ai_calibration import AssistantFeedback
from app.db.models.invitation import StudentInvitation


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
    "ActivityCategory",
    "ActivityStatus",
    "StudentActivity",
    "AssessmentMark",
    "AttendanceRecord",
    "AttendanceStatus",
    "EvidenceFile",
    "AssistantFeedback",
    "StudentInvitation",
]