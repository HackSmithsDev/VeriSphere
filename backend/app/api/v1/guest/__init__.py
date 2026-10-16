from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import Course
from app.db.session import get_db
from app.schemas.academic import CourseResponse


router = APIRouter(tags=["public"])


@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(db: AsyncSession = Depends(get_db)) -> list[CourseResponse]:
    courses = await db.scalars(select(Course).order_by(Course.name))
    return [
        CourseResponse(
            id=course.id,
            name=course.name,
            duration_years=course.duration_years,
        )
        for course in courses
    ]


@router.get("/announcements")
async def list_announcements() -> list[dict[str, str]]:
    return [
        {
            "id": "welcome",
            "title": "Welcome to VeriSphere",
            "body": "Track your learning milestones and keep verified evidence of your progress in one place.",
            "published_at": "2026-01-01",
        }
    ]
