from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.db.models.activity import ActivityCategory, ActivityStatus


class ActivityCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: ActivityCategory
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=10, max_length=4000)
    issuer: str | None = Field(default=None, max_length=255)
    achieved_on: date | None = None
    proof_url: HttpUrl | None = Field(default=None, max_length=2048)
    evidence_file_id: str | None = Field(default=None, min_length=36, max_length=36)

    @model_validator(mode="after")
    def require_one_evidence_source(self) -> "ActivityCreate":
        if bool(self.proof_url) == bool(self.evidence_file_id):
            raise ValueError("Provide exactly one evidence link or uploaded evidence file.")
        return self


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: ActivityCategory
    title: str
    description: str
    issuer: str | None
    achieved_on: date | None
    proof_url: str
    evidence_file_id: str | None
    status: ActivityStatus
    review_feedback: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ActivitySubmissionResponse(ActivityResponse):
    student: str


class ActivityReview(BaseModel):
    decision: Literal["verified", "needs_revision"]
    feedback: str = Field(default="", max_length=4000)
