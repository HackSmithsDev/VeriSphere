from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AssistantChatRequest(BaseModel):
    messages: list[AssistantMessage] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def require_user_message_last(self) -> "AssistantChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The last message must be from the user.")
        return self


class AssistantChatResponse(BaseModel):
    reply: str
    provider: Literal["Groq", "Gemini"]
