import asyncio
import json

import httpx
import pytest

from app.services.ai import advisor


def test_student_prompt_uses_learning_coach_instructions() -> None:
    messages = advisor.build_provider_messages(
        "student",
        "Course: Computer Science",
        [{"role": "user", "content": "What next?"}],
    )

    assert messages[0]["role"] == "system"
    assert "learning coach" in messages[0]["content"]
    assert "Course: Computer Science" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "What next?"}


def test_teacher_prompt_preserves_human_review_and_anonymity() -> None:
    messages = advisor.build_provider_messages(
        "teacher",
        "Submission 1: Data Structures",
        [{"role": "user", "content": "Suggest feedback."}],
    )

    assert "anonymized" in messages[0]["content"]
    assert "teacher is responsible" in messages[0]["content"]
    assert messages[1]["role"] == "user"


def test_gemini_is_used_when_groq_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def groq_fails(_: advisor.ChatHistory) -> str:
        calls.append("Groq")
        raise advisor.AIProviderError("provider failure")

    async def gemini_succeeds(_: advisor.ChatHistory) -> str:
        calls.append("Gemini")
        return "Try the next chapter."

    monkeypatch.setattr(advisor, "GROQ_API_KEY", "configured")
    monkeypatch.setattr(advisor, "GEMINI_API_KEY", "configured")
    monkeypatch.setattr(advisor, "_request_groq", groq_fails)
    monkeypatch.setattr(advisor, "_request_gemini", gemini_succeeds)

    answer, provider = asyncio.run(
        advisor.generate_advice(
            "student",
            "One milestone remains.",
            [{"role": "user", "content": "What should I do next?"}],
        )
    )

    assert calls == ["Groq", "Gemini"]
    assert answer == "Try the next chapter."
    assert provider == "Gemini"


def test_missing_provider_keys_raise_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(advisor, "GROQ_API_KEY", "")
    monkeypatch.setattr(advisor, "GEMINI_API_KEY", "")

    with pytest.raises(advisor.AIProvidersNotConfigured):
        asyncio.run(
            advisor.generate_advice(
                "student",
                "No progress yet.",
                [{"role": "user", "content": "Where do I start?"}],
            )
        )


@pytest.mark.parametrize(
    ("provider", "response_body", "expected_path", "expected_header"),
    [
        (
            "groq",
            {"choices": [{"message": {"content": "Start with the next lesson."}}]},
            "/openai/v1/chat/completions",
            ("authorization", "Bearer test-groq-key"),
        ),
        (
            "gemini",
            {"candidates": [{"content": {"parts": [{"text": "Review your feedback."}]}}]},
            "/v1beta/models/gemini-2.5-flash:generateContent",
            ("x-goog-api-key", "test-gemini-key"),
        ),
    ],
)
def test_provider_request_uses_configured_api(
    provider: str,
    response_body: dict,
    expected_path: str,
    expected_header: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=response_body)

    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(
        advisor.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )

    history = [
        {"role": "system", "content": "Use the learning context."},
        {"role": "user", "content": "What should I study?"},
    ]
    if provider == "groq":
        monkeypatch.setattr(advisor, "GROQ_API_KEY", "test-groq-key")
        result = asyncio.run(advisor._request_groq(history))
    else:
        monkeypatch.setattr(advisor, "GEMINI_API_KEY", "test-gemini-key")
        result = asyncio.run(advisor._request_gemini(history))

    assert result
    assert len(requests) == 1
    assert requests[0].url.path == expected_path
    assert requests[0].headers[expected_header[0]] == expected_header[1]
    assert expected_header[1] not in str(requests[0].url)
    assert json.loads(requests[0].content)
