from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_calibration import AssistantFeedback
from app.db.models.user import User


async def record_feedback(
    user: User,
    provider: str,
    helpful: bool,
    db: AsyncSession,
) -> AssistantFeedback:
    feedback = AssistantFeedback(
        user_id=user.id,
        provider=provider,
        helpful=helpful,
    )
    db.add(feedback)
    await db.flush()
    return feedback
