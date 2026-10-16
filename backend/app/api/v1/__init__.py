from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.assistant import router as assistant_router
from app.api.v1.auth import router as auth_router
from app.api.v1.guest import router as guest_router
from app.api.v1.student import router as student_router
from app.api.v1.teacher import router as teacher_router


router = APIRouter()
router.include_router(auth_router)
router.include_router(guest_router)
router.include_router(student_router)
router.include_router(teacher_router)
router.include_router(admin_router)
router.include_router(assistant_router)