from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.models.academic import Chapter, Subject
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.user import StudentProfile, User
from app.db.session import get_db
from app.schemas.academic import MilestoneReview


router = APIRouter(prefix="/teacher", tags=["teacher"])
teacher_only = require_roles("teacher")


@router.get("/dashboard")
async def dashboard(
    _: User = Depends(teacher_only), db: AsyncSession = Depends(get_db)
) -> dict:
    pending = await db.scalar(
        select(func.count(StudentMilestone.id)).where(
            StudentMilestone.status == MilestoneStatus.PENDING_VERIFICATION
        )
    )
    students = await db.scalar(select(func.count(StudentProfile.id)))
    return {"stats": {"pending_reviews": pending or 0, "students": students or 0}}


@router.get("/submissions")
async def list_submissions(
    _: User = Depends(teacher_only), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    rows = await db.execute(
        select(StudentMilestone, StudentProfile, Chapter, Subject, User)
        .join(StudentProfile, StudentMilestone.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .join(Chapter, StudentMilestone.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .where(StudentMilestone.status == MilestoneStatus.PENDING_VERIFICATION)
        .order_by(StudentMilestone.updated_at)
    )
    return [
        {
            "id": milestone.id,
            "student": f"{student.first_name} {student.last_name}",
            "email": user.email,
            "title": chapter.title,
            "subject": subject.name,
            "submission": milestone.submission_payload or {},
            "updated_at": milestone.updated_at.isoformat(),
        }
        for milestone, student, chapter, subject, user in rows
    ]


@router.post("/submissions/{milestone_id}/review")
async def review_submission(
    milestone_id: int,
    review: MilestoneReview,
    _: User = Depends(teacher_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if review.decision not in {"verified", "needs_revision"}:
        raise HTTPException(
            status_code=422, detail="Decision must be verified or needs_revision."
        )
    milestone = await db.get(StudentMilestone, milestone_id)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if milestone.status != MilestoneStatus.PENDING_VERIFICATION:
        raise HTTPException(
            status_code=409, detail="This submission is no longer awaiting review."
        )
    milestone.status = (
        MilestoneStatus.VERIFIED
        if review.decision == "verified"
        else MilestoneStatus.IN_PROGRESS
    )
    milestone.teacher_feedback = review.feedback.strip() or None
    if review.decision == "verified":
        next_milestone = await db.scalar(
            select(StudentMilestone)
            .join(Chapter, StudentMilestone.chapter_id == Chapter.id)
            .join(Subject, Chapter.subject_id == Subject.id)
            .where(
                StudentMilestone.student_id == milestone.student_id,
                StudentMilestone.status == MilestoneStatus.LOCKED,
            )
            .order_by(Subject.semester, Subject.id, Chapter.sequence_order)
            .limit(1)
        )
        if next_milestone is not None:
            next_milestone.status = MilestoneStatus.IN_PROGRESS
    await db.flush()
    return {"id": milestone.id, "status": milestone.status.value}
