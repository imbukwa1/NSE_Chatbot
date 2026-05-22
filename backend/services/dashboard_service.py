from datetime import datetime

from sqlalchemy.orm import Session

from models.stock_view import StockView
from models.user import User
from services.favorites_service import list_favorites
from services.market_service import market_payload, stock_snapshot, trending_stocks
from services.profile_service import get_recent_searches
from services.watchlist_service import list_watchlist


def record_stock_view(db: Session, user: User, ticker: str) -> None:
    stock = stock_snapshot(ticker)
    if not stock:
        return
    db.add(StockView(user_id=user.id, ticker=stock["ticker"]))
    db.commit()


def recent_stock_views(db: Session, user: User, limit: int = 10) -> list[dict]:
    views = (
        db.query(StockView)
        .filter(StockView.user_id == user.id)
        .order_by(StockView.viewed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "ticker": view.ticker,
            "viewed_at": view.viewed_at,
            "stock": stock_snapshot(view.ticker),
        }
        for view in views
    ]


def dashboard_summary(db: Session, user: User) -> dict:
    overview = market_payload()
    return {
        "market_status": overview["status"],
        "top_gainers": overview["top_gainers"],
        "top_losers": overview["top_losers"],
        "trending_stocks": trending_stocks(),
        "favorites": list_favorites(db, user),
        "watchlist": list_watchlist(db, user),
        "recent_searches": [
            {
                "id": item.id,
                "search_query": item.search_query,
                "created_at": item.created_at,
            }
            for item in get_recent_searches(db, user, limit=10)
        ],
        "recent_views": recent_stock_views(db, user, limit=10),
        "generated_at": datetime.now().isoformat(),
    }

