from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.ai.advisor import (
    AIProviderError,
    AIProvidersNotConfigured,
    build_learning_context,
    generate_advice,
)


router = APIRouter(prefix="/assistant", tags=["AI assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
async def chat(
    payload: AssistantChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssistantChatResponse:
    if user.role not in {UserRole.STUDENT, UserRole.TEACHER}:
        raise HTTPException(
            status_code=403,
            detail="The AI assistant is available to students and faculty.",
        )
    try:
        context = await build_learning_context(user, db)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    try:
        reply, provider = await generate_advice(
            user.role.value,
            context,
            [message.model_dump() for message in payload.messages],
        )
    except AIProvidersNotConfigured as error:
        raise HTTPException(
            status_code=503,
            detail="Configure GROQ_API_KEY or GEMINI_API_KEY to enable the AI assistant.",
        ) from error
    except AIProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="The AI assistant providers are unavailable. Please try again shortly.",
        ) from error

    return AssistantChatResponse(reply=reply, provider=provider)
