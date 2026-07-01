from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    category: str = Field(..., min_length=2, max_length=80)
    question: str = Field(..., min_length=3, max_length=255)
    answer: str = Field(..., min_length=3)
    source: str | None = Field(default=None, max_length=255)


class KnowledgeBaseUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=80)
    question: str | None = Field(default=None, min_length=3, max_length=255)
    answer: str | None = Field(default=None, min_length=3)
    source: str | None = Field(default=None, max_length=255)


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: str | None = None
    slug: str | None = None
    category: str
    subcategory: str | None = None
    question: str
    aliases: str | None = None
    answer: str
    answer_markdown: str | None = None
    keywords: str | None = None
    difficulty: str | None = None
    related_questions: str | None = None
    source: str | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime
