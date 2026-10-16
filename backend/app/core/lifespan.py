import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.core.config import INITIAL_ADMIN_EMAIL, INITIAL_ADMIN_PASSWORD
from app.core.database import SessionFactory, engine
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Chapter, Course, Subject, User
from app.db.models.user import UserRole


logger = logging.getLogger(__name__)


async def initialize_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with SessionFactory() as session:
        course = await session.scalar(select(Course).order_by(Course.id).limit(1))
        if course is None:
            course = Course(name="B.Tech Computer Science", duration_years=4)
            session.add(course)
            await session.flush()
            subjects = [
                Subject(
                    course_id=course.id,
                    code="CS101",
                    name="Programming Foundations",
                    semester=1,
                ),
                Subject(
                    course_id=course.id,
                    code="CS102",
                    name="Data Structures",
                    semester=1,
                ),
                Subject(
                    course_id=course.id,
                    code="CS201",
                    name="Web Application Development",
                    semester=2,
                ),
            ]
            session.add_all(subjects)
            await session.flush()
            session.add_all(
                [
                    Chapter(
                        subject_id=subjects[0].id,
                        sequence_order=1,
                        title="Python Fundamentals",
                        description="Build a small, tested command-line application.",
                    ),
                    Chapter(
                        subject_id=subjects[0].id,
                        sequence_order=2,
                        title="Programming Essentials",
                        description="Practice core programming patterns and explain your approach.",
                    ),
                    Chapter(
                        subject_id=subjects[1].id,
                        sequence_order=1,
                        title="Data Structures Portfolio",
                        description="Demonstrate core structures with working examples.",
                    ),
                    Chapter(
                        subject_id=subjects[2].id,
                        sequence_order=1,
                        title="Full-stack Project",
                        description="Ship and document a small web application.",
                    ),
                ]
            )

        admin_email = INITIAL_ADMIN_EMAIL.strip().lower()
        admin_password = INITIAL_ADMIN_PASSWORD
        if bool(admin_email) != bool(admin_password):
            raise RuntimeError(
                "INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD must be set together."
            )
        if admin_email:
            if len(admin_password) < 12:
                raise RuntimeError(
                    "INITIAL_ADMIN_PASSWORD must contain at least 12 characters."
                )
            try:
                admin_email = str(TypeAdapter(EmailStr).validate_python(admin_email))
            except ValidationError as error:
                raise RuntimeError(
                    "INITIAL_ADMIN_EMAIL must be a valid email address."
                ) from error
            admin = await session.scalar(select(User).where(User.email == admin_email))
            if admin is None:
                session.add(
                    User(
                        email=admin_email,
                        hashed_password=hash_password(admin_password),
                        role=UserRole.ADMIN,
                    )
                )
                logger.info("Created initial administrator account.")
            elif admin.role != UserRole.ADMIN:
                raise RuntimeError(
                    "INITIAL_ADMIN_EMAIL is already assigned to a non-administrator."
                )
        await session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    try:
        await initialize_database()
        yield
    finally:
        await engine.dispose()
