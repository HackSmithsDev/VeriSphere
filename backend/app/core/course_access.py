from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import teacher_course_assignment
from app.db.models.user import User, UserRole


async def assigned_course_ids(user: User, db: AsyncSession) -> set[int] | None:
    if user.role == UserRole.ADMIN:
        return None
    return set(
        await db.scalars(
            select(teacher_course_assignment.c.course_id).where(
                teacher_course_assignment.c.teacher_id == user.id
            )
        )
    )


async def can_access_course(
    user: User, course_id: int, db: AsyncSession
) -> bool:
    courses = await assigned_course_ids(user, db)
    return courses is None or course_id in courses
