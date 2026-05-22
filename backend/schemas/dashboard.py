from pydantic import BaseModel


class StockSearchResult(BaseModel):
    ticker: str
    name: str
    price: float | None = None
    sector: str | None = None
    source: str | None = None


class DashboardSummary(BaseModel):
    market_status: dict
    top_gainers: list[dict]
    top_losers: list[dict]
    trending_stocks: list[dict]
    favorites: list[dict]
    recent_searches: list[dict]
    generated_at: str

