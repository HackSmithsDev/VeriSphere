from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.db.models.academic import Course
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.user import StudentProfile, TeacherProfile, User, UserRole
from app.db.session import get_db
from app.schemas.academic import CourseCreate, TeacherCreate


router = APIRouter(prefix="/admin", tags=["administration"])
admin_only = require_roles("admin")


@router.get("/overview")
async def overview(
    _: User = Depends(admin_only), db: AsyncSession = Depends(get_db)
) -> dict:
    users = await db.scalar(select(func.count(User.id)))
    students = await db.scalar(select(func.count(StudentProfile.id)))
    teachers = await db.scalar(select(func.count(TeacherProfile.id)))
    reviews = await db.scalar(
        select(func.count(StudentMilestone.id)).where(
            StudentMilestone.status == MilestoneStatus.PENDING_VERIFICATION
        )
    )
    courses = await db.scalar(select(func.count(Course.id)))
    return {
        "stats": {
            "users": users or 0,
            "students": students or 0,
            "teachers": teachers or 0,
            "pending_reviews": reviews or 0,
            "courses": courses or 0,
        }
    }


@router.get("/users")
async def list_users(
    _: User = Depends(admin_only), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    users = await db.scalars(select(User).order_by(User.created_at.desc()).limit(200))
    return [
        {
            "id": user.id,
            "email": user.email,
            "role": user.role.value,
            "active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


@router.post("/courses", status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await db.scalar(select(Course.id).where(Course.name == payload.name))
    if existing is not None:
        raise HTTPException(status_code=409, detail="A course with this name exists.")
    course = Course(name=payload.name.strip(), duration_years=payload.duration_years)
    db.add(course)
    await db.flush()
    return {"id": course.id, "name": course.name, "duration_years": course.duration_years}


@router.post("/teachers", status_code=status.HTTP_201_CREATED)
async def create_teacher(
    payload: TeacherCreate,
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    email = payload.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    existing = await db.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email exists.")
    user = User(email=email, hashed_password=hash_password(payload.password), role=UserRole.TEACHER)
    user.teacher_profile = TeacherProfile(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        department=payload.department.strip(),
    )
    db.add(user)
    await db.flush()
    return {"id": user.id, "email": user.email, "role": user.role.value}
