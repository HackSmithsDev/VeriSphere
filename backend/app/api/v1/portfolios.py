import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.models.user import StudentProfile, User
from app.db.session import get_db
from app.services.portfolio import build_portfolio, build_resume_html


router = APIRouter(tags=["student portfolios"])
student_only = require_roles("student")


@router.get("/student/portfolio")
async def get_student_portfolio(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> dict:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    portfolio = await build_portfolio(profile, db)
    portfolio["share_url"] = (
        f"/portfolio/{profile.portfolio_share_token}"
        if profile.portfolio_share_token
        else None
    )
    return portfolio


@router.get("/student/portfolio/resume", response_class=HTMLResponse)
async def export_student_resume(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    portfolio = await build_portfolio(profile, db)
    return HTMLResponse(
        content=build_resume_html(portfolio),
        headers={"Content-Disposition": 'attachment; filename="verisphere-resume.html"'},
    )


@router.post("/student/portfolio/share")
async def enable_portfolio_sharing(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    if profile.portfolio_share_token is None:
        profile.portfolio_share_token = secrets.token_urlsafe(32)
        await db.flush()
    return {"share_url": f"/portfolio/{profile.portfolio_share_token}"}


@router.delete("/student/portfolio/share", status_code=204)
async def disable_portfolio_sharing(
    user: User = Depends(student_only), db: AsyncSession = Depends(get_db)
) -> None:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    profile.portfolio_share_token = None


@router.get("/portfolios/{share_token}")
async def get_shared_portfolio(
    share_token: str, db: AsyncSession = Depends(get_db)
) -> dict:
    profile = await db.scalar(
        select(StudentProfile).where(
            StudentProfile.portfolio_share_token == share_token
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")
    return await build_portfolio(profile, db)


@router.get("/portfolios/{share_token}/resume", response_class=HTMLResponse)
async def export_shared_resume(
    share_token: str, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    profile = await db.scalar(
        select(StudentProfile).where(
            StudentProfile.portfolio_share_token == share_token
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")
    portfolio = await build_portfolio(profile, db)
    return HTMLResponse(
        content=build_resume_html(portfolio),
        headers={"Content-Disposition": 'attachment; filename="verisphere-resume.html"'},
    )
