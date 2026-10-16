from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.models.academic import Chapter, Course, Subject
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.user import StudentProfile, User
from app.db.session import get_db
from app.schemas.academic import MilestoneSubmission


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
    milestone.submission_payload = submission.model_dump(
        mode="json", exclude_none=True
    )
    milestone.status = MilestoneStatus.PENDING_VERIFICATION
    milestone.teacher_feedback = None
    await db.flush()
    return {"id": milestone.id, "status": milestone.status.value}
