from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.user import User
from services.chat_service import api_success
from services.dashboard_service import record_stock_view
from services.market_cache import get_market_status
from services.market_service import get_chart_data, market_payload, search_stocks, trending_stocks

router = APIRouter(tags=["Market"])


@router.get("/stocks/search")
def stock_search(q: str = Query(..., min_length=1)):
    return api_success(
        "Stock search completed successfully",
        {"results": search_stocks(q)},
    )


@router.get("/stocks/{ticker}/chart")
def stock_chart(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    if current_user:
        record_stock_view(db, current_user, ticker)
    return api_success(
        "Stock chart data retrieved successfully",
        {"chart": get_chart_data(ticker)},
    )


@router.get("/market/overview")
def get_market_overview_api():
    return api_success("Market overview retrieved successfully", {"market": market_payload()})


@router.get("/market/status")
def get_market_status_api():
    return api_success(
        "Market status retrieved successfully",
        {"status": get_market_status()},
    )


@router.get("/market/top-gainers")
def get_top_gainers():
    return api_success("Top gainers retrieved successfully", market_payload("top_gainers"))


@router.get("/market/top-losers")
def get_top_losers():
    return api_success("Top losers retrieved successfully", market_payload("top_losers"))


@router.get("/market/most-active")
def get_most_active():
    return api_success("Most active stocks retrieved successfully", market_payload("most_active"))


@router.get("/market/trending")
def get_trending():
    return api_success(
        "Trending stocks retrieved successfully",
        {"stocks": trending_stocks(), "source": "market_intelligence"},
    )
