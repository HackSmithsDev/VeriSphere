from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator


class CourseResponse(BaseModel):
    id: int
    name: str
    duration_years: int


class MilestoneSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    summary: str = Field(min_length=10, max_length=4000)
    proof_url: HttpUrl | None = None
    evidence_file_id: str | None = Field(default=None, min_length=36, max_length=36)


class MilestoneReview(BaseModel):
    decision: Literal["verified", "needs_revision"]
    feedback: str = Field(default="", max_length=4000)


class CourseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=3, max_length=255)
    duration_years: int = Field(ge=1, le=8)


class TeacherCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    department: str = Field(min_length=2, max_length=255)
    course_ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_course_ids(self) -> "TeacherCreate":
        if len(self.course_ids) != len(set(self.course_ids)) or any(
            course_id < 1 for course_id in self.course_ids
        ):
            raise ValueError("Course IDs must be unique positive integers.")
        return self


class TeacherCourseAssignment(BaseModel):
    course_ids: list[int]

    @model_validator(mode="after")
    def require_unique_course_ids(self) -> "TeacherCourseAssignment":
        if len(self.course_ids) != len(set(self.course_ids)) or any(
            course_id < 1 for course_id in self.course_ids
        ):
            raise ValueError("Course IDs must be unique positive integers.")
        return self
