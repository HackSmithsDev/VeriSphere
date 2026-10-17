from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.models.activity import ActivityStatus, StudentActivity
from app.db.models.records import EvidenceFile
from app.db.models.user import StudentProfile, User
from app.db.session import get_db
from app.schemas.activity import ActivityCreate, ActivityResponse


router = APIRouter(prefix="/student/activities", tags=["student activities"])
student_only = require_roles("student")


async def _student_profile(user: User, db: AsyncSession) -> StudentProfile:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return profile


@router.get("", response_model=list[ActivityResponse])
async def list_activities(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> list[StudentActivity]:
    profile = await _student_profile(user, db)
    activities = await db.scalars(
        select(StudentActivity)
        .where(StudentActivity.student_id == profile.id)
        .order_by(StudentActivity.created_at.desc())
    )
    return list(activities)


@router.post(
    "", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED
)
async def submit_activity(
    payload: ActivityCreate,
    user: User = Depends(student_only),
    db: AsyncSession = Depends(get_db),
) -> StudentActivity:
    profile = await _student_profile(user, db)
    if payload.evidence_file_id is not None:
        evidence = await db.get(EvidenceFile, payload.evidence_file_id)
        if evidence is None or evidence.student_id != profile.id:
            raise HTTPException(
                status_code=404, detail="Uploaded evidence file not found."
            )
    activity = StudentActivity(
        student_id=profile.id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        issuer=payload.issuer,
        achieved_on=payload.achieved_on,
        proof_url=str(payload.proof_url) if payload.proof_url else "",
        evidence_file_id=payload.evidence_file_id,
        status=ActivityStatus.PENDING_VERIFICATION,
    )
    db.add(activity)
    await db.flush()
    return activity


@router.put("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    payload: ActivityCreate,
    user: User = Depends(student_only),
    db: AsyncSession = Depends(get_db),
) -> StudentActivity:
    profile = await _student_profile(user, db)
    activity = await db.scalar(
        select(StudentActivity).where(
            StudentActivity.id == activity_id,
            StudentActivity.student_id == profile.id,
        )
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found.")
    if activity.status == ActivityStatus.VERIFIED:
        raise HTTPException(
            status_code=409, detail="A verified activity cannot be edited."
        )
    if payload.evidence_file_id is not None:
        evidence = await db.get(EvidenceFile, payload.evidence_file_id)
        if evidence is None or evidence.student_id != profile.id:
            raise HTTPException(
                status_code=404, detail="Uploaded evidence file not found."
            )
    activity.category = payload.category
    activity.title = payload.title
    activity.description = payload.description
    activity.issuer = payload.issuer
    activity.achieved_on = payload.achieved_on
    activity.proof_url = str(payload.proof_url) if payload.proof_url else ""
    activity.evidence_file_id = payload.evidence_file_id
    activity.status = ActivityStatus.PENDING_VERIFICATION
    activity.reviewer_id = None
    activity.reviewed_at = None
    activity.review_feedback = None
    await db.flush()
    return activity
