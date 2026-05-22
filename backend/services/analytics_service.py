from collections import Counter
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.chat import ChatMessage, ChatSession
from models.recent_search import RecentSearch
from models.stock_view import StockView
from models.user import User


def admin_analytics(db: Session) -> dict:
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active.is_(True)).count()
    total_conversations = db.query(ChatSession).count()
    total_chatbot_requests = (
        db.query(ChatMessage).filter(ChatMessage.sender_type == "user").count()
    )

    popular_queries = (
        db.query(RecentSearch.search_query, func.count(RecentSearch.id).label("count"))
        .group_by(RecentSearch.search_query)
        .order_by(func.count(RecentSearch.id).desc())
        .limit(5)
        .all()
    )
    viewed = (
        db.query(StockView.ticker, func.count(StockView.id).label("count"))
        .group_by(StockView.ticker)
        .order_by(func.count(StockView.id).desc())
        .limit(5)
        .all()
    )
    search_terms = [row.search_query.upper() for row in db.query(RecentSearch).all()]
    tickers = ["SCOM", "KCB", "EQTY", "COOP", "EABL", "KQ"]
    stock_counts = Counter()
    for query in search_terms:
        for ticker in tickers:
            if ticker in query:
                stock_counts[ticker] += 1

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_conversations": total_conversations,
        "most_searched_stocks": [
            {"ticker": ticker, "count": count}
            for ticker, count in stock_counts.most_common(5)
        ],
        "most_popular_queries": [
            {"query": row.search_query, "count": row.count}
            for row in popular_queries
        ],
        "top_viewed_companies": [
            {"ticker": row.ticker, "count": row.count}
            for row in viewed
        ],
        "total_chatbot_requests": total_chatbot_requests,
        "market_request_frequency": {
            "source": "lightweight_counter",
            "tracked_endpoints": [
                "/market/overview",
                "/market/top-gainers",
                "/market/top-losers",
                "/market/most-active",
            ],
        },
        "generated_at": datetime.now().isoformat(),
    }

