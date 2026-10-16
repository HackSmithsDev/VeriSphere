import asyncio

from fastapi import FastAPI
import httpx
import pytest

from app.api.v1 import assistant as assistant_api
from app.core.dependencies import get_current_user
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.services.ai import advisor


def _app_for_role(role: UserRole) -> FastAPI:
    application = FastAPI()
    application.include_router(assistant_api.router)
    application.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email="test@example.com",
        role=role,
        hashed_password="unused",
    )
    application.dependency_overrides[get_db] = lambda: None
    return application


async def _post_chat(application: FastAPI) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        return await client.post(
            "/assistant/chat",
            json={"messages": [{"role": "user", "content": "What should I do?"}]},
        )


@pytest.mark.parametrize("role", [UserRole.STUDENT, UserRole.TEACHER])
def test_student_and_teacher_can_chat(
    role: UserRole, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_context(user: User, _: object) -> str:
        return f"context for {user.role.value}"

    async def fake_advice(
        selected_role: str, context: str, _: advisor.ChatHistory
    ) -> tuple[str, str]:
        assert selected_role == role.value
        assert context == f"context for {role.value}"
        return "Try this next.", "Groq"

    monkeypatch.setattr(assistant_api, "build_learning_context", fake_context)
    monkeypatch.setattr(assistant_api, "generate_advice", fake_advice)

    response = asyncio.run(_post_chat(_app_for_role(role)))

    assert response.status_code == 200
    assert response.json() == {"reply": "Try this next.", "provider": "Groq"}


def test_admin_cannot_use_assistant() -> None:
    response = asyncio.run(_post_chat(_app_for_role(UserRole.ADMIN)))

    assert response.status_code == 403
