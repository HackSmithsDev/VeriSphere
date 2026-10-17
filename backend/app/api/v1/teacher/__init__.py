from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.course_access import assigned_course_ids, can_access_course
from app.core.dependencies import require_roles
from app.db.models.academic import Chapter, Subject
from app.db.models.activity import ActivityStatus, StudentActivity
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.user import StudentProfile, User
from app.db.session import get_db
from app.schemas.activity import (
    ActivityResponse,
    ActivityReview,
    ActivitySubmissionResponse,
)
from app.schemas.academic import MilestoneReview


router = APIRouter(prefix="/teacher", tags=["teacher"])
teacher_only = require_roles("teacher")
staff_only = require_roles("teacher", "admin")


@router.get("/dashboard")
async def dashboard(
    user: User = Depends(teacher_only), db: AsyncSession = Depends(get_db)
) -> dict:
    course_ids = await assigned_course_ids(user, db)
    if not course_ids:
        return {
            "stats": {
                "pending_reviews": 0,
                "pending_activity_reviews": 0,
                "students": 0,
            }
        }
    pending = await db.scalar(
        select(func.count(StudentMilestone.id))
        .join(Chapter, StudentMilestone.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .where(
            StudentMilestone.status == MilestoneStatus.PENDING_VERIFICATION,
            Subject.course_id.in_(course_ids),
        )
    )
    students = await db.scalar(
        select(func.count(StudentProfile.id)).where(
            StudentProfile.course_id.in_(course_ids)
        )
    )
    pending_activities = await db.scalar(
        select(func.count(StudentActivity.id))
        .join(StudentProfile, StudentActivity.student_id == StudentProfile.id)
        .where(
            StudentActivity.status == ActivityStatus.PENDING_VERIFICATION,
            StudentProfile.course_id.in_(course_ids),
        )
    )
    return {
        "stats": {
            "pending_reviews": pending or 0,
            "pending_activity_reviews": pending_activities or 0,
            "students": students or 0,
        }
    }


@router.get("/submissions")
async def list_submissions(
    user: User = Depends(teacher_only), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    course_ids = await assigned_course_ids(user, db)
    if not course_ids:
        return []
    rows = await db.execute(
        select(StudentMilestone, StudentProfile, Chapter, Subject, User)
        .join(StudentProfile, StudentMilestone.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .join(Chapter, StudentMilestone.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .where(
            StudentMilestone.status == MilestoneStatus.PENDING_VERIFICATION,
            Subject.course_id.in_(course_ids),
        )
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
            "evidence_file_id": milestone.evidence_file_id,
            "updated_at": milestone.updated_at.isoformat(),
        }
        for milestone, student, chapter, subject, user in rows
    ]


@router.post("/submissions/{milestone_id}/review")
async def review_submission(
    milestone_id: int,
    review: MilestoneReview,
    user: User = Depends(teacher_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if review.decision not in {"verified", "needs_revision"}:
        raise HTTPException(
            status_code=422, detail="Decision must be verified or needs_revision."
        )
    milestone = await db.get(StudentMilestone, milestone_id)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    subject_course_id = await db.scalar(
        select(Subject.course_id)
        .join(Chapter, Chapter.subject_id == Subject.id)
        .where(Chapter.id == milestone.chapter_id)
    )
    if subject_course_id is None or not await can_access_course(
        user, subject_course_id, db
    ):
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


@router.get("/activities", response_model=list[ActivitySubmissionResponse])
async def list_pending_activities(
    user: User = Depends(staff_only), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    course_ids = await assigned_course_ids(user, db)
    query = (
        select(StudentActivity, StudentProfile)
        .join(StudentProfile, StudentActivity.student_id == StudentProfile.id)
        .where(StudentActivity.status == ActivityStatus.PENDING_VERIFICATION)
        .order_by(StudentActivity.created_at)
    )
    if course_ids is not None:
        if not course_ids:
            return []
        query = query.where(StudentProfile.course_id.in_(course_ids))
    rows = await db.execute(query)
    return [
        {
            **ActivityResponse.model_validate(activity).model_dump(mode="json"),
            "student": f"{student.first_name} {student.last_name}",
        }
        for activity, student in rows
    ]


@router.post("/activities/{activity_id}/review")
async def review_activity(
    activity_id: int,
    review: ActivityReview,
    user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course_ids = await assigned_course_ids(user, db)
    query = (
        select(StudentActivity)
        .join(StudentProfile, StudentActivity.student_id == StudentProfile.id)
        .where(StudentActivity.id == activity_id)
    )
    if course_ids is not None:
        query = query.where(StudentProfile.course_id.in_(course_ids))
    activity = await db.scalar(query)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found.")
    if activity.status != ActivityStatus.PENDING_VERIFICATION:
        raise HTTPException(
            status_code=409, detail="This activity is no longer awaiting review."
        )
    activity.status = ActivityStatus(review.decision)
    activity.review_feedback = review.feedback.strip() or None
    activity.reviewer_id = user.id
    activity.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    return {"id": activity.id, "status": activity.status.value}
