import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import FRONTEND_BASE_URL, STUDENT_INVITATION_EXPIRE_HOURS
from app.core.security import hash_password
from app.db.models.academic import Chapter, Course, Subject
from app.db.models.invitation import StudentInvitation
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.user import StudentProfile, User, UserRole
from app.services.excel.parser import StudentImportRow


class InvitationNotFound(RuntimeError):
    pass


class InvitationAlreadyUsed(RuntimeError):
    pass


class InvitationAccountExists(RuntimeError):
    pass


class InvitationExpired(RuntimeError):
    pass


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_invitation(
    student: StudentImportRow,
) -> tuple[StudentInvitation, str]:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC).replace(tzinfo=None)
    invitation = StudentInvitation(
        email=student.email,
        course_id=student.course_id,
        first_name=student.first_name,
        last_name=student.last_name,
        token_hash=hash_invitation_token(token),
        expires_at=now + timedelta(hours=STUDENT_INVITATION_EXPIRE_HOURS),
    )
    link = f"{FRONTEND_BASE_URL}/set-password?{urlencode({'token': token})}"
    return invitation, link


async def accept_student_invitation(
    token: str, password: str, db: AsyncSession
) -> User:
    if not token or len(token) > 256:
        raise InvitationNotFound
    invitation = await db.scalar(
        select(StudentInvitation).where(
            StudentInvitation.token_hash == hash_invitation_token(token)
        )
    )
    if invitation is None:
        raise InvitationNotFound
    if invitation.accepted_at is not None:
        raise InvitationAlreadyUsed
    now = datetime.now(UTC).replace(tzinfo=None)
    if invitation.expires_at <= now:
        raise InvitationExpired
    if await db.scalar(select(User.id).where(User.email == invitation.email)):
        raise InvitationAccountExists
    course = await db.get(Course, invitation.course_id)
    if course is None:
        raise InvitationNotFound

    user = User(
        email=invitation.email,
        hashed_password=hash_password(password),
        role=UserRole.STUDENT,
    )
    user.student_profile = StudentProfile(
        course_id=course.id,
        first_name=invitation.first_name,
        last_name=invitation.last_name,
    )
    db.add(user)
    await db.flush()
    chapters = await db.scalars(
        select(Chapter)
        .join(Subject, Chapter.subject_id == Subject.id)
        .where(Subject.course_id == course.id)
        .order_by(Subject.semester, Subject.id, Chapter.sequence_order)
    )
    for index, chapter in enumerate(chapters):
        db.add(
            StudentMilestone(
                student_id=user.student_profile.id,
                chapter_id=chapter.id,
                status=(
                    MilestoneStatus.IN_PROGRESS
                    if index == 0
                    else MilestoneStatus.LOCKED
                ),
            )
        )
    invitation.accepted_at = now
    await db.flush()
    return user
