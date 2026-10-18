import logging

import httpx


logger = logging.getLogger(__name__)


class AIProviderError(RuntimeError):
    pass


async def request_groq(
    messages: list[dict[str, str]], api_key: str, model: str
) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.35,
                    "max_tokens": 1000,
                },
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as error:
        logger.warning("Groq request failed with HTTP %s.", error.response.status_code)
        raise AIProviderError("Groq returned an unsuccessful response.") from error
    except httpx.RequestError as error:
        logger.warning("Groq request failed: %s.", type(error).__name__)
        raise AIProviderError("Groq could not be reached.") from error
    except ValueError as error:
        raise AIProviderError("Groq returned an invalid response.") from error

    try:
        text = data["choices"][0]["message"]["content"]
    except (IndexError, KeyError, TypeError) as error:
        raise AIProviderError("Groq returned an invalid response.") from error
    if not isinstance(text, str) or not text.strip():
        raise AIProviderError("Groq returned an empty response.")
    return text.strip()


async def request_gemini(
    messages: list[dict[str, str]], api_key: str, model: str
) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    system_message, *history = messages
    contents = [
        {
            "role": "model" if message["role"] == "assistant" else "user",
            "parts": [{"text": message["content"]}],
        }
        for message in history
    ]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": api_key},
                json={
                    "systemInstruction": {
                        "parts": [{"text": system_message["content"]}],
                    },
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.35,
                        "maxOutputTokens": 1000,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as error:
        logger.warning(
            "Gemini request failed with HTTP %s.", error.response.status_code
        )
        raise AIProviderError("Gemini returned an unsuccessful response.") from error
    except httpx.RequestError as error:
        logger.warning("Gemini request failed: %s.", type(error).__name__)
        raise AIProviderError("Gemini could not be reached.") from error
    except ValueError as error:
        raise AIProviderError("Gemini returned an invalid response.") from error

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (IndexError, KeyError, TypeError) as error:
        raise AIProviderError("Gemini returned an invalid response.") from error
    if not isinstance(text, str) or not text.strip():
        raise AIProviderError("Gemini returned an empty response.")
    return text.strip()
