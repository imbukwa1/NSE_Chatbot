from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FavoriteCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class FavoriteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    ticker: str
    created_at: datetime
    stock: dict | None = None

