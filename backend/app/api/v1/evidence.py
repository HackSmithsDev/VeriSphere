import logging
import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import UPLOAD_DIR
from app.core.dependencies import get_current_user, require_roles
from app.db.models.activity import ActivityStatus, StudentActivity
from app.db.models.milestone import MilestoneStatus, StudentMilestone
from app.db.models.records import EvidenceFile
from app.db.models.user import StudentProfile, User, UserRole
from app.db.session import get_db


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/student/evidence", tags=["student evidence"])
student_only = require_roles("student")
MAX_EVIDENCE_SIZE = 10 * 1024 * 1024
ALLOWED_SIGNATURES = (
    (b"%PDF-", "application/pdf", ".pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
)


def _safe_filename(filename: str | None, extension: str) -> str:
    name = (filename or "evidence").replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    stem = Path(name or "evidence").stem or "evidence"
    return f"{stem[:255 - len(extension)]}{extension}"


def _file_response(evidence: EvidenceFile) -> FileResponse:
    file_path = (UPLOAD_DIR / evidence.storage_name).resolve()
    if file_path.parent != UPLOAD_DIR:
        logger.error("Evidence storage metadata contains an invalid path.")
        raise HTTPException(status_code=500, detail="Evidence file is unavailable.")
    if not file_path.is_file():
        logger.error("Evidence file %s is missing from storage.", evidence.id)
        raise HTTPException(status_code=404, detail="Evidence file is unavailable.")
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=evidence.original_name,
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    file: UploadFile = File(...),
    user: User = Depends(student_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if profile is None:
        await file.close()
        raise HTTPException(status_code=404, detail="Student profile not found.")

    first_chunk = await file.read(64 * 1024)
    match = next(
        (
            (media_type, extension)
            for signature, media_type, extension in ALLOWED_SIGNATURES
            if first_chunk.startswith(signature)
        ),
        None,
    )
    if match is None:
        await file.close()
        raise HTTPException(
            status_code=415,
            detail="Evidence must be a PDF, PNG, or JPEG file.",
        )

    media_type, extension = match
    storage_name = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / storage_name
    total_size = 0
    upload_complete = False
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(
            file_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(descriptor, "wb") as output:
            chunk = first_chunk
            while chunk:
                total_size += len(chunk)
                if total_size > MAX_EVIDENCE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Evidence files must be 10 MB or smaller.",
                    )
                output.write(chunk)
                chunk = await file.read(64 * 1024)
        upload_complete = True
    except HTTPException:
        raise
    except OSError as error:
        logger.exception("Could not persist an uploaded evidence file.")
        raise HTTPException(
            status_code=500, detail="Could not save the uploaded evidence file."
        ) from error
    finally:
        try:
            await file.close()
        finally:
            if not upload_complete:
                file_path.unlink(missing_ok=True)

    evidence = EvidenceFile(
        id=str(uuid4()),
        student_id=profile.id,
        storage_name=storage_name,
        original_name=_safe_filename(file.filename, extension),
        media_type=media_type,
        size_bytes=total_size,
    )
    db.add(evidence)
    try:
        await db.flush()
    except SQLAlchemyError:
        file_path.unlink(missing_ok=True)
        raise
    return {
        "id": evidence.id,
        "filename": evidence.original_name,
        "media_type": evidence.media_type,
        "size_bytes": evidence.size_bytes,
    }


@router.get("/{evidence_id}")
async def download_evidence(
    evidence_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    evidence = await db.get(EvidenceFile, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    profile = await db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    )
    if user.role == UserRole.STUDENT:
        allowed = profile is not None and profile.id == evidence.student_id
    elif user.role in {UserRole.TEACHER, UserRole.ADMIN}:
        activity_link = await db.scalar(
            select(StudentActivity.id).where(
                StudentActivity.evidence_file_id == evidence.id
            )
        )
        milestone_link = await db.scalar(
            select(StudentMilestone.id).where(
                StudentMilestone.evidence_file_id == evidence.id
            )
        )
        allowed = activity_link is not None or milestone_link is not None
    else:
        allowed = False
    if not allowed:
        raise HTTPException(
            status_code=403, detail="You cannot access this evidence file."
        )

    return _file_response(evidence)


@router.get("/shared/{share_token}/{evidence_id}")
async def download_shared_evidence(
    share_token: str, evidence_id: str, db: AsyncSession = Depends(get_db)
) -> FileResponse:
    profile = await db.scalar(
        select(StudentProfile).where(
            StudentProfile.portfolio_share_token == share_token
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    evidence = await db.scalar(
        select(EvidenceFile).where(
            EvidenceFile.id == evidence_id,
            EvidenceFile.student_id == profile.id,
        )
    )
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    activity = await db.scalar(
        select(StudentActivity.id).where(
            StudentActivity.evidence_file_id == evidence.id,
            StudentActivity.student_id == profile.id,
            StudentActivity.status == ActivityStatus.VERIFIED,
        )
    )
    milestone = await db.scalar(
        select(StudentMilestone.id).where(
            StudentMilestone.evidence_file_id == evidence.id,
            StudentMilestone.student_id == profile.id,
            StudentMilestone.status == MilestoneStatus.VERIFIED,
        )
    )
    if activity is None and milestone is None:
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    return _file_response(evidence)
