from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.db.models.academic import Course, Subject
from app.db.models.activity import ActivityStatus, StudentActivity
from app.db.models.ai_calibration import AssistantFeedback
from app.db.models.invitation import StudentInvitation
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.records import AssessmentMark, AttendanceRecord, AttendanceStatus
from app.db.models.user import StudentProfile, TeacherProfile, User, UserRole
from app.db.session import get_db
from app.schemas.academic import (
    CourseCreate,
    TeacherCourseAssignment,
    TeacherCreate,
)
from app.services.excel import export_report_workbook
from app.services.excel.exporter import XLSX_MEDIA_TYPE
from app.services.excel import (
    MAX_STUDENT_IMPORT_ROWS,
    SpreadsheetValidationError,
    build_student_import_template,
    parse_student_workbook,
)
from app.services.email import dispatch_student_invitation, ensure_email_configured
from app.services.student_invitations import new_invitation


router = APIRouter(prefix="/admin", tags=["administration"])
admin_only = require_roles("admin")
MAX_STUDENT_IMPORT_SIZE = 5 * 1024 * 1024


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


@router.post("/students/import", status_code=status.HTTP_202_ACCEPTED)
async def import_students(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        await file.close()
        raise HTTPException(status_code=415, detail="Upload an .xlsx workbook.")
    try:
        content = await file.read(MAX_STUDENT_IMPORT_SIZE + 1)
    finally:
        await file.close()
    if len(content) > MAX_STUDENT_IMPORT_SIZE:
        raise HTTPException(status_code=413, detail="Workbook must be 5 MB or smaller.")
    try:
        students = parse_student_workbook(content)
    except SpreadsheetValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors) from error
    if len(students) > MAX_STUDENT_IMPORT_ROWS:
        raise HTTPException(
            status_code=422,
            detail=f"Import is limited to {MAX_STUDENT_IMPORT_ROWS} students.",
        )
    try:
        ensure_email_configured()
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail="Configure SMTP before importing and inviting students.",
        ) from error

    course_ids = {student.course_id for student in students}
    existing_courses = set(
        await db.scalars(select(Course.id).where(Course.id.in_(course_ids)))
    )
    invalid_course_rows = [
        f"Row {student.row_number}: course_id {student.course_id} does not exist."
        for student in students
        if student.course_id not in existing_courses
    ]
    if invalid_course_rows:
        raise HTTPException(status_code=422, detail=invalid_course_rows)

    emails = [student.email for student in students]
    existing_users = set(
        await db.scalars(select(User.email).where(User.email.in_(emails)))
    )
    if existing_users:
        duplicates = [
            f"Row {student.row_number}: an account already exists for {student.email}."
            for student in students
            if student.email in existing_users
        ]
        raise HTTPException(status_code=409, detail=duplicates)

    existing_invitations = {
        invitation.email: invitation
        for invitation in await db.scalars(
            select(StudentInvitation).where(StudentInvitation.email.in_(emails))
        )
    }
    now = datetime.now(UTC).replace(tzinfo=None)
    active_duplicates = [
        f"Row {student.row_number}: an active invitation already exists for {student.email}."
        for student in students
        if (
            (invitation := existing_invitations.get(student.email)) is not None
            and invitation.accepted_at is None
            and invitation.expires_at > now
        )
    ]
    if active_duplicates:
        raise HTTPException(status_code=409, detail=active_duplicates)

    for student in students:
        invitation, link = new_invitation(student)
        previous = existing_invitations.get(student.email)
        if previous is None:
            db.add(invitation)
        else:
            previous.course_id = invitation.course_id
            previous.first_name = invitation.first_name
            previous.last_name = invitation.last_name
            previous.token_hash = invitation.token_hash
            previous.expires_at = invitation.expires_at
            previous.accepted_at = None
        background_tasks.add_task(
            dispatch_student_invitation,
            student.email,
            f"{student.first_name} {student.last_name}",
            link,
        )
    await db.flush()
    await db.commit()
    return {"invited": len(students)}


@router.get("/students/import-template.xlsx")
async def student_import_template(
    _: User = Depends(admin_only),
) -> Response:
    return Response(
        content=build_student_import_template(),
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": 'attachment; filename="verisphere-student-import-template.xlsx"'
        },
    )


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
    return await build_activity_report(db)


async def build_activity_report(db: AsyncSession) -> dict:
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
    return await build_academic_report(db)


async def build_academic_report(db: AsyncSession) -> dict:
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


@router.get("/reports/activities/export.xlsx")
async def export_activity_report(
    _: User = Depends(admin_only), db: AsyncSession = Depends(get_db)
) -> Response:
    report = await build_activity_report(db)
    return Response(
        content=export_report_workbook("activities", report),
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": 'attachment; filename="verisphere-activities.xlsx"'
        },
    )


@router.get("/reports/academics/export.xlsx")
async def export_academic_report(
    _: User = Depends(admin_only), db: AsyncSession = Depends(get_db)
) -> Response:
    report = await build_academic_report(db)
    return Response(
        content=export_report_workbook("academics", report),
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": 'attachment; filename="verisphere-academics.xlsx"'
        },
    )


@router.get("/assistant/feedback")
async def assistant_feedback_report(
    _: User = Depends(admin_only), db: AsyncSession = Depends(get_db)
) -> dict:
    rows = await db.execute(
        select(
            AssistantFeedback.provider,
            func.count(AssistantFeedback.id),
            func.sum(case((AssistantFeedback.helpful.is_(True), 1), else_=0)),
        )
        .group_by(AssistantFeedback.provider)
        .order_by(AssistantFeedback.provider)
    )
    return {
        "providers": [
            {
                "provider": provider,
                "responses_rated": count,
                "helpful": helpful or 0,
                "helpfulness_percentage": round((helpful or 0) * 100 / count, 1)
                if count
                else None,
            }
            for provider, count, helpful in rows
        ]
    }
