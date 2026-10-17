import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.models.academic import Chapter, Course, Subject
from app.db.models.activity import ActivityStatus, StudentActivity
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.user import StudentProfile, User
from app.db.session import get_db


router = APIRouter(tags=["student portfolios"])
student_only = require_roles("student")


async def _build_portfolio(
    profile: StudentProfile, db: AsyncSession
) -> dict:
    course = await db.get(Course, profile.course_id)
    activity_rows = await db.scalars(
        select(StudentActivity)
        .where(
            StudentActivity.student_id == profile.id,
            StudentActivity.status == ActivityStatus.VERIFIED,
        )
        .order_by(StudentActivity.achieved_on.desc(), StudentActivity.created_at.desc())
    )
    milestone_rows = await db.execute(
        select(StudentMilestone, Chapter, Subject)
        .join(Chapter, StudentMilestone.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .where(
            StudentMilestone.student_id == profile.id,
            StudentMilestone.status == MilestoneStatus.VERIFIED,
        )
        .order_by(Subject.semester, Subject.id, Chapter.sequence_order)
    )
    return {
        "student": {
            "name": f"{profile.first_name} {profile.last_name}",
            "course": course.name if course else None,
            "semester": profile.current_semester,
        },
        "academic_milestones": [
            {
                "title": chapter.title,
                "subject": subject.name,
                "semester": subject.semester,
                "evidence_file_id": milestone.evidence_file_id,
                "verified_at": milestone.updated_at,
            }
            for milestone, chapter, subject in milestone_rows
        ],
        "activities": [
            {
                "category": activity.category.value,
                "title": activity.title,
                "description": activity.description,
                "issuer": activity.issuer,
                "achieved_on": activity.achieved_on,
                "proof_url": activity.proof_url,
                "evidence_file_id": activity.evidence_file_id,
                "verified_at": activity.reviewed_at,
            }
            for activity in activity_rows
        ],
        "share_enabled": profile.portfolio_share_token is not None,
    }


@router.get("/student/portfolio")
async def get_student_portfolio(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> dict:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    portfolio = await _build_portfolio(profile, db)
    portfolio["share_url"] = (
        f"/portfolio/{profile.portfolio_share_token}"
        if profile.portfolio_share_token
        else None
    )
    return portfolio


@router.post("/student/portfolio/share")
async def enable_portfolio_sharing(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    if profile.portfolio_share_token is None:
        profile.portfolio_share_token = secrets.token_urlsafe(32)
        await db.flush()
    return {"share_url": f"/portfolio/{profile.portfolio_share_token}"}


@router.delete("/student/portfolio/share", status_code=204)
async def disable_portfolio_sharing(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> None:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    profile.portfolio_share_token = None


@router.get("/portfolios/{share_token}")
async def get_shared_portfolio(
    share_token: str, db: AsyncSession = Depends(get_db)
) -> dict:
    profile = await db.scalar(
        select(StudentProfile).where(
            StudentProfile.portfolio_share_token == share_token
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")
    return await _build_portfolio(profile, db)
