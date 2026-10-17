from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.db.models.academic import Course, Subject
from app.db.models.activity import ActivityStatus, StudentActivity
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.records import AssessmentMark, AttendanceRecord, AttendanceStatus
from app.db.models.user import StudentProfile, TeacherProfile, User, UserRole
from app.db.session import get_db
from app.schemas.academic import (
    CourseCreate,
    TeacherCourseAssignment,
    TeacherCreate,
)


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
    activity_reviews = await db.scalar(
        select(func.count(StudentActivity.id)).where(
            StudentActivity.status == ActivityStatus.PENDING_VERIFICATION
        )
    )
    courses = await db.scalar(select(func.count(Course.id)))
    return {
        "stats": {
            "users": users or 0,
            "students": students or 0,
            "teachers": teachers or 0,
            "pending_reviews": reviews or 0,
            "pending_activity_reviews": activity_reviews or 0,
            "courses": courses or 0,
        }
    }


@router.get("/users")
async def list_users(
    _: User = Depends(admin_only), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    users = await db.scalars(
        select(User)
        .options(selectinload(User.assigned_courses))
        .order_by(User.created_at.desc())
        .limit(200)
    )
    return [
        {
            "id": user.id,
            "email": user.email,
            "role": user.role.value,
            "active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "courses": [
                {"id": course.id, "name": course.name}
                for course in user.assigned_courses
            ]
            if user.role == UserRole.TEACHER
            else [],
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
    if payload.course_ids:
        courses = list(
            await db.scalars(select(Course).where(Course.id.in_(payload.course_ids)))
        )
        if len(courses) != len(payload.course_ids):
            raise HTTPException(status_code=422, detail="One or more courses do not exist.")
        user.assigned_courses = courses
    db.add(user)
    await db.flush()
    return {"id": user.id, "email": user.email, "role": user.role.value}


@router.put("/teachers/{teacher_id}/courses")
async def assign_teacher_courses(
    teacher_id: int,
    payload: TeacherCourseAssignment,
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    teacher = await db.scalar(
        select(User)
        .where(User.id == teacher_id, User.role == UserRole.TEACHER)
        .options(selectinload(User.assigned_courses))
    )
    if teacher is None:
        raise HTTPException(status_code=404, detail="Faculty account not found.")
    courses = (
        list(await db.scalars(select(Course).where(Course.id.in_(payload.course_ids))))
        if payload.course_ids
        else []
    )
    if len(courses) != len(payload.course_ids):
        raise HTTPException(status_code=422, detail="One or more courses do not exist.")
    teacher.assigned_courses = courses
    await db.flush()
    return {
        "teacher_id": teacher.id,
        "courses": [{"id": course.id, "name": course.name} for course in courses],
    }


@router.get("/reports/activities")
async def activity_report(
    _: User = Depends(admin_only), db: AsyncSession = Depends(get_db)
) -> dict:
    total = await db.scalar(select(func.count(StudentActivity.id))) or 0
    verified = (
        await db.scalar(
            select(func.count(StudentActivity.id)).where(
                StudentActivity.status == ActivityStatus.VERIFIED
            )
        )
        or 0
    )
    pending = (
        await db.scalar(
            select(func.count(StudentActivity.id)).where(
                StudentActivity.status == ActivityStatus.PENDING_VERIFICATION
            )
        )
        or 0
    )
    by_category = await db.execute(
        select(StudentActivity.category, func.count(StudentActivity.id))
        .group_by(StudentActivity.category)
        .order_by(StudentActivity.category)
    )
    by_status = await db.execute(
        select(StudentActivity.status, func.count(StudentActivity.id))
        .group_by(StudentActivity.status)
        .order_by(StudentActivity.status)
    )
    return {
        "total_activities": total,
        "verified_activities": verified,
        "pending_verification": pending,
        "needs_revision": total - verified - pending,
        "by_category": [
            {"category": category.value, "count": count}
            for category, count in by_category
        ],
        "by_status": [
            {"status": state.value, "count": count} for state, count in by_status
        ],
    }


@router.get("/reports/academics")
async def academic_report(
    _: User = Depends(admin_only), db: AsyncSession = Depends(get_db)
) -> dict:
    attendance_rows = await db.execute(
        select(
            Course.name,
            Subject.code,
            Subject.name,
            func.count(AttendanceRecord.id),
            func.sum(
                case(
                    (AttendanceRecord.status == AttendanceStatus.PRESENT, 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (AttendanceRecord.status == AttendanceStatus.ABSENT, 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (AttendanceRecord.status == AttendanceStatus.EXCUSED, 1),
                    else_=0,
                )
            ),
        )
        .join(Subject, Subject.course_id == Course.id)
        .outerjoin(AttendanceRecord, AttendanceRecord.subject_id == Subject.id)
        .group_by(Course.name, Subject.id, Subject.code, Subject.name)
        .order_by(Course.name, Subject.semester, Subject.name)
    )
    mark_rows = await db.execute(
        select(
            Course.name,
            Subject.code,
            Subject.name,
            func.count(AssessmentMark.id),
            func.avg(AssessmentMark.score * 100 / AssessmentMark.maximum_score),
        )
        .join(Subject, Subject.course_id == Course.id)
        .outerjoin(AssessmentMark, AssessmentMark.subject_id == Subject.id)
        .group_by(Course.name, Subject.id, Subject.code, Subject.name)
        .order_by(Course.name, Subject.semester, Subject.name)
    )
    attendance = [
        {
            "course": course,
            "subject_code": code,
            "subject": name,
            "sessions_recorded": sessions,
            "present": present or 0,
            "absent": absent or 0,
            "excused": excused or 0,
            "attendance_percentage": round((present or 0) * 100 / (sessions - (excused or 0)), 1)
            if sessions > (excused or 0)
            else None,
        }
        for course, code, name, sessions, present, absent, excused in attendance_rows
    ]
    assessments = [
        {
            "course": course,
            "subject_code": code,
            "subject": name,
            "assessments_recorded": count,
            "average_percentage": round(float(average), 1) if average is not None else None,
        }
        for course, code, name, count, average in mark_rows
    ]
    return {
        "attendance": attendance,
        "assessments": assessments,
        "students": await db.scalar(select(func.count(StudentProfile.id))) or 0,
        "subjects": await db.scalar(select(func.count(Subject.id))) or 0,
    }
