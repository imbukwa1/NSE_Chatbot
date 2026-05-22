from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WatchlistCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class WatchlistUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=255)


class WatchlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    ticker: str
    notes: str | None
    created_at: datetime
    stock: dict | None = None

