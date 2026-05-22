from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=160)


class ChatMessageCreate(BaseModel):
    message_text: str = Field(..., min_length=1, max_length=4000)

    @field_validator("message_text")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty.")
        return cleaned


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    sender_type: str
    message_text: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionResponse):
    messages: list[ChatMessageResponse] = []


class StoredChatResponse(BaseModel):
    session: ChatSessionResponse
    user_message: ChatMessageResponse
    ai_message: ChatMessageResponse
    chatbot_response: dict

