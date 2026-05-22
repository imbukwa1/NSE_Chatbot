from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    member_since: datetime
    display_name: str
    investor_level: str
    bio: str | None = None


class RecentSearchCreate(BaseModel):
    search_query: str = Field(..., min_length=1, max_length=255)

    @field_validator("search_query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Search query cannot be empty.")
        return cleaned


class RecentSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    search_query: str
    created_at: datetime

