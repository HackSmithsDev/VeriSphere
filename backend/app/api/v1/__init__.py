from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.activities import router as activities_router
from app.api.v1.assistant import router as assistant_router
from app.api.v1.auth import router as auth_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.guest import router as guest_router
from app.api.v1.portfolios import router as portfolios_router
from app.api.v1.records import router as records_router
from app.api.v1.student import router as student_router
from app.api.v1.teacher import router as teacher_router


router = APIRouter()
router.include_router(auth_router)
router.include_router(guest_router)
router.include_router(student_router)
router.include_router(teacher_router)
router.include_router(admin_router)
router.include_router(activities_router)
router.include_router(portfolios_router)
router.include_router(records_router)
router.include_router(evidence_router)
router.include_router(assistant_router)