from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.course_access import assigned_course_ids, can_access_course
from app.core.dependencies import require_roles
from app.db.models.academic import Subject
from app.db.models.records import (
    AssessmentMark,
    AttendanceRecord,
    AttendanceStatus,
)
from app.db.models.user import StudentProfile, User
from app.db.session import get_db
from app.schemas.records import AssessmentEntry, AttendanceEntry


router = APIRouter(tags=["academic records"])
student_only = require_roles("student")
staff_only = require_roles("teacher", "admin")


async def _validate_student_subject(
    student_id: int, subject_id: int, user: User, db: AsyncSession
) -> tuple[StudentProfile, Subject]:
    student = await db.get(StudentProfile, student_id)
    subject = await db.get(Subject, subject_id)
    if student is None or subject is None:
        raise HTTPException(status_code=404, detail="Student or subject not found.")
    if student.course_id != subject.course_id:
        raise HTTPException(
            status_code=422, detail="The subject does not belong to the student's course."
        )
    if not await can_access_course(user, subject.course_id, db):
        raise HTTPException(status_code=404, detail="Student or subject not found.")
    return student, subject


@router.get("/student/academic-records")
async def get_student_academic_records(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> dict:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    attendance_rows = await db.execute(
        select(
            Subject.id,
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
        .join(AttendanceRecord, AttendanceRecord.subject_id == Subject.id)
        .where(AttendanceRecord.student_id == profile.id)
        .group_by(Subject.id, Subject.code, Subject.name)
        .order_by(Subject.name)
    )
    marks = await db.execute(
        select(AssessmentMark, Subject)
        .join(Subject, AssessmentMark.subject_id == Subject.id)
        .where(AssessmentMark.student_id == profile.id)
        .order_by(AssessmentMark.assessment_date.desc(), AssessmentMark.id.desc())
    )
    return {
        "attendance": [
            {
                "subject_id": subject_id,
                "subject_code": subject_code,
                "subject": subject_name,
                "sessions": sessions,
                "present": present or 0,
                "absent": absent or 0,
                "excused": excused or 0,
                "percentage": round((present or 0) * 100 / (sessions - (excused or 0)), 1)
                if sessions > (excused or 0)
                else None,
            }
            for (
                subject_id,
                subject_code,
                subject_name,
                sessions,
                present,
                absent,
                excused,
            ) in attendance_rows
        ],
        "marks": [
            {
                "id": mark.id,
                "subject_id": subject.id,
                "subject_code": subject.code,
                "subject": subject.name,
                "title": mark.title,
                "score": mark.score,
                "maximum_score": mark.maximum_score,
                "percentage": round(mark.score * 100 / mark.maximum_score, 1),
                "assessment_date": mark.assessment_date.isoformat(),
            }
            for mark, subject in marks
        ],
    }


@router.get("/teacher/academic-options")
async def get_academic_options(
    user: User = Depends(staff_only), db: AsyncSession = Depends(get_db)
) -> dict:
    course_ids = await assigned_course_ids(user, db)
    student_query = select(
        StudentProfile.id,
        StudentProfile.first_name,
        StudentProfile.last_name,
        StudentProfile.course_id,
    ).order_by(StudentProfile.last_name, StudentProfile.first_name)
    subject_query = select(
        Subject.id, Subject.code, Subject.name, Subject.course_id
    ).order_by(Subject.course_id, Subject.semester, Subject.name)
    if course_ids is not None:
        student_query = student_query.where(StudentProfile.course_id.in_(course_ids))
        subject_query = subject_query.where(Subject.course_id.in_(course_ids))
    students = await db.execute(student_query)
    subjects = await db.execute(subject_query)
    return {
        "students": [
            {
                "id": student_id,
                "name": f"{first_name} {last_name}",
                "course_id": course_id,
            }
            for student_id, first_name, last_name, course_id in students
        ],
        "subjects": [
            {
                "id": subject_id,
                "code": code,
                "name": name,
                "course_id": course_id,
            }
            for subject_id, code, name, course_id in subjects
        ],
    }


@router.post("/teacher/attendance")
async def record_attendance(
    payload: AttendanceEntry,
    user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _validate_student_subject(payload.student_id, payload.subject_id, user, db)
    record = await db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id == payload.student_id,
            AttendanceRecord.subject_id == payload.subject_id,
            AttendanceRecord.attendance_date == payload.attendance_date,
        )
    )
    if record is None:
        record = AttendanceRecord(
            student_id=payload.student_id,
            subject_id=payload.subject_id,
            attendance_date=payload.attendance_date,
            status=payload.status,
            recorded_by=user.id,
        )
        db.add(record)
    else:
        record.status = payload.status
        record.recorded_by = user.id
    await db.flush()
    return {"id": record.id, "status": record.status.value}


@router.post("/teacher/marks")
async def record_assessment_mark(
    payload: AssessmentEntry,
    user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _validate_student_subject(payload.student_id, payload.subject_id, user, db)
    if payload.score > payload.maximum_score:
        raise HTTPException(
            status_code=422, detail="Score cannot exceed the maximum score."
        )
    mark = AssessmentMark(
        student_id=payload.student_id,
        subject_id=payload.subject_id,
        recorded_by=user.id,
        title=payload.title,
        score=payload.score,
        maximum_score=payload.maximum_score,
        assessment_date=payload.assessment_date,
    )
    db.add(mark)
    await db.flush()
    return {"id": mark.id, "score": mark.score, "maximum_score": mark.maximum_score}
