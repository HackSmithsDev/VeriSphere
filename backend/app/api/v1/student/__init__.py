from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import FRONTEND_BASE_URL
from app.core.dependencies import require_roles
from app.db.models.academic import Chapter, Course, Subject
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.records import EvidenceFile
from app.db.models.user import StudentProfile, User
from app.db.session import get_db
from app.schemas.academic import MilestoneSubmission
from app.services.telemetry import (
    GitHubProfileNotFound,
    GitHubRateLimitExceeded,
    GitHubServiceError,
    LinkedInNotConfigured,
    LinkedInOAuthError,
    create_authorization_url,
    exchange_code_for_profile,
    get_github_profile,
    read_authorization_state,
)


router = APIRouter(prefix="/student", tags=["student"])
student_only = require_roles("student")


async def _profile_for(user: User, db: AsyncSession) -> StudentProfile:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return profile


@router.get("/dashboard")
async def dashboard(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> dict:
    profile = await _profile_for(user, db)
    course = await db.get(Course, profile.course_id)
    milestones = list(
        await db.scalars(
            select(StudentMilestone)
            .where(StudentMilestone.student_id == profile.id)
            .order_by(StudentMilestone.id)
        )
    )
    total = len(milestones)
    verified = sum(m.status == MilestoneStatus.VERIFIED for m in milestones)
    pending = sum(m.status == MilestoneStatus.PENDING_VERIFICATION for m in milestones)
    recent = await db.execute(
        select(StudentMilestone, Chapter, Subject)
        .join(Chapter, StudentMilestone.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .where(StudentMilestone.student_id == profile.id)
        .order_by(StudentMilestone.updated_at.desc())
        .limit(5)
    )
    return {
        "student": {
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": user.email,
            "semester": profile.current_semester,
            "course": course.name if course else "Course unavailable",
        },
        "stats": {
            "total_milestones": total,
            "verified_milestones": verified,
            "pending_reviews": pending,
            "completion_percent": round(verified * 100 / total) if total else 0,
        },
        "recent_activity": [
            {
                "id": milestone.id,
                "title": chapter.title,
                "subject": subject.name,
                "status": milestone.status.value,
                "updated_at": milestone.updated_at.isoformat(),
            }
            for milestone, chapter, subject in recent
        ],
    }


@router.get("/milestones")
async def list_milestones(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    profile = await _profile_for(user, db)
    rows = await db.execute(
        select(StudentMilestone, Chapter, Subject)
        .join(Chapter, StudentMilestone.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .where(StudentMilestone.student_id == profile.id)
        .order_by(Subject.semester, Subject.id, Chapter.sequence_order)
    )
    return [
        {
            "id": milestone.id,
            "chapter_id": chapter.id,
            "title": chapter.title,
            "description": chapter.description,
            "subject": subject.name,
            "subject_code": subject.code,
            "semester": subject.semester,
            "status": milestone.status.value,
            "submission": milestone.submission_payload,
            "evidence_file_id": milestone.evidence_file_id,
            "feedback": milestone.teacher_feedback,
        }
        for milestone, chapter, subject in rows
    ]


@router.post("/milestones/{milestone_id}/submit")
async def submit_milestone(
    milestone_id: int,
    submission: MilestoneSubmission,
    user: User = Depends(student_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile = await _profile_for(user, db)
    milestone = await db.scalar(
        select(StudentMilestone).where(
            StudentMilestone.id == milestone_id,
            StudentMilestone.student_id == profile.id,
        )
    )
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found.")
    if milestone.status == MilestoneStatus.VERIFIED:
        raise HTTPException(
            status_code=409, detail="A verified milestone cannot be resubmitted."
        )
    if milestone.status != MilestoneStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=409,
            detail="Only an in-progress milestone can be submitted or resubmitted.",
        )
    if submission.evidence_file_id is not None:
        evidence = await db.get(EvidenceFile, submission.evidence_file_id)
        if evidence is None or evidence.student_id != profile.id:
            raise HTTPException(
                status_code=404, detail="Uploaded evidence file not found."
            )
    milestone.submission_payload = submission.model_dump(
        mode="json", exclude_none=True
    )
    milestone.evidence_file_id = submission.evidence_file_id
    milestone.status = MilestoneStatus.PENDING_VERIFICATION
    milestone.teacher_feedback = None
    await db.flush()
    return {"id": milestone.id, "status": milestone.status.value}


@router.get("/telemetry/github/{username}")
async def github_profile_telemetry(
    username: str,
    user: User = Depends(student_only),
) -> dict:
    try:
        return await get_github_profile(username)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except GitHubProfileNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except GitHubRateLimitExceeded as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except GitHubServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/telemetry/linkedin/authorize")
async def linkedin_authorization(
    user: User = Depends(student_only),
) -> dict[str, str]:
    try:
        return {"authorization_url": create_authorization_url(user.id)}
    except LinkedInNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/telemetry/linkedin/profile")
async def linkedin_profile(
    user: User = Depends(student_only),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | bool | None]:
    profile = await _profile_for(user, db)
    return {
        "name": profile.linkedin_name,
        "picture_url": profile.linkedin_picture_url,
        "connected": profile.linkedin_name is not None,
    }


@router.get("/telemetry/linkedin/callback")
async def linkedin_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if error:
        raise HTTPException(
            status_code=400, detail="LinkedIn authorization was not completed."
        )
    if not code or not state:
        raise HTTPException(
            status_code=400, detail="LinkedIn authorization response is incomplete."
        )
    try:
        user_id = read_authorization_state(state)
        profile = await exchange_code_for_profile(code)
    except LinkedInNotConfigured as exception:
        raise HTTPException(status_code=503, detail=str(exception)) from exception
    except LinkedInOAuthError as exception:
        raise HTTPException(status_code=400, detail=str(exception)) from exception

    student = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    student.linkedin_name = profile.get("name") or "LinkedIn profile"
    student.linkedin_picture_url = profile.get("picture")
    return RedirectResponse(
        url=f"{FRONTEND_BASE_URL}/?linkedin=connected", status_code=303
    )
