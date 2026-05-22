from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminAnalyticsResponse(BaseModel):
    total_users: int
    active_users: int
    total_conversations: int
    most_searched_stocks: list[dict]
    most_popular_queries: list[dict]
    top_viewed_companies: list[dict]
    total_chatbot_requests: int
    market_request_frequency: dict
    generated_at: str


class ScraperLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scrape_time: datetime
    status: str
    records_updated: int
    error_message: str | None


class SystemLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    description: str
    created_at: datetime

