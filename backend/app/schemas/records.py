from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.records import AttendanceStatus


class AttendanceEntry(BaseModel):
    student_id: int = Field(gt=0)
    subject_id: int = Field(gt=0)
    attendance_date: date
    status: AttendanceStatus


class AssessmentEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    student_id: int = Field(gt=0)
    subject_id: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=255)
    score: float = Field(ge=0)
    maximum_score: float = Field(gt=0)
    assessment_date: date


class AcademicRecordReportQuery(BaseModel):
    course_id: int | None = Field(default=None, gt=0)


class ActivityExportQuery(BaseModel):
    status: Literal["all", "verified", "pending_verification", "needs_revision"] = "all"
