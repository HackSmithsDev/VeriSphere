from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import Chapter, Course, Subject
from app.db.models.activity import ActivityStatus, StudentActivity
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.user import StudentProfile


async def build_portfolio(
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
