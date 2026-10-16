from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.academic import Chapter, Course, Subject
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.user import StudentProfile, User, UserRole
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse


router = APIRouter(prefix="/auth", tags=["authentication"])


async def _user_response(user: User, db: AsyncSession) -> UserResponse:
    if user.role == UserRole.STUDENT:
        profile = await db.scalar(
            select(StudentProfile).where(StudentProfile.user_id == user.id)
        )
        if profile:
            return UserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                first_name=profile.first_name,
                last_name=profile.last_name,
            )
    return UserResponse(id=user.id, email=user.email, role=user.role)


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    email = payload.email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    existing = await db.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email exists.")
    course = await db.get(Course, payload.course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="The selected course was not found.")
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        role=UserRole.STUDENT,
    )
    user.student_profile = StudentProfile(
        course_id=course.id,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
    )
    db.add(user)
    await db.flush()
    profile = user.student_profile
    chapters = await db.scalars(
        select(Chapter)
        .join(Subject, Chapter.subject_id == Subject.id)
        .where(Subject.course_id == course.id)
        .order_by(Subject.semester, Subject.id, Chapter.sequence_order)
    )
    for index, chapter in enumerate(chapters):
        db.add(
            StudentMilestone(
                student_id=profile.id,
                chapter_id=chapter.id,
                status=(
                    MilestoneStatus.IN_PROGRESS
                    if index == 0
                    else MilestoneStatus.LOCKED
                ),
            )
        )
    await db.flush()
    return {
        "access_token": create_access_token(str(user.id)),
        "token_type": "bearer",
        "user": (await _user_response(user, db)).model_dump(mode="json"),
    }


@router.post("/login", response_model=dict)
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    user = await db.scalar(
        select(User).where(User.email == payload.email.strip().lower())
    )
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Contact your administrator.",
        )
    return {
        "access_token": create_access_token(str(user.id)),
        "token_type": "bearer",
        "user": (await _user_response(user, db)).model_dump(mode="json"),
    }


@router.get("/me", response_model=UserResponse)
async def read_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await _user_response(user, db)