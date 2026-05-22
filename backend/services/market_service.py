from datetime import datetime
from typing import Any

import database
from services.market_intelligence import SECTOR_BY_TICKER, get_market_overview
from services.structured_data import get_all_stock_data, get_stock_data


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def stock_snapshot(ticker: str, include_history: bool = False) -> dict[str, Any] | None:
    stock = get_stock_data(normalize_ticker(ticker), include_history=include_history)
    if not stock:
        return None
    return {
        **stock,
        "sector": SECTOR_BY_TICKER.get(stock.get("ticker"), "Other"),
    }


def require_stock(ticker: str) -> dict[str, Any]:
    stock = stock_snapshot(ticker)
    if not stock:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {normalize_ticker(ticker)} is not supported.",
        )
    return stock


def search_stocks(query: str, limit: int = 10) -> list[dict[str, Any]]:
    cleaned = query.strip().lower()
    if not cleaned:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty.",
        )

    stocks = get_all_stock_data(include_history=False)
    matches = []
    for stock in stocks:
        ticker = str(stock.get("ticker", "")).lower()
        name = str(stock.get("name", "")).lower()
        if cleaned in ticker or cleaned in name:
            matches.append(
                {
                    **stock,
                    "sector": SECTOR_BY_TICKER.get(stock.get("ticker"), "Other"),
                }
            )

    if matches:
        return matches[:limit]

    # Optional Pinecone-assisted fuzzy lookup. Any issue falls back quietly.
    try:
        from services.pinecone_service import query_documents

        pinecone_matches = query_documents(query, namespace="stocks", top_k=limit)
        tickers = [match.get("ticker") for match in pinecone_matches if match.get("ticker")]
        for ticker in tickers:
            stock = stock_snapshot(ticker)
            if stock:
                matches.append(stock)
    except Exception:
        pass

    return matches[:limit]


def get_chart_data(ticker: str) -> dict[str, Any]:
    normalized = normalize_ticker(ticker)
    stock = stock_snapshot(normalized, include_history=True)
    if not stock:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {normalized} is not supported.",
        )

    history = database.get_price_history(normalized, days=365)
    points = [
        {
            "timestamp": item.get("recorded_at"),
            "price": item.get("price"),
        }
        for item in reversed(history)
        if item.get("price") is not None
    ]
    if not points:
        points = [
            {"timestamp": item.get("date"), "price": item.get("price")}
            for item in stock.get("history", [])
            if item.get("price") is not None
        ]

    return {
        "ticker": stock["ticker"],
        "name": stock["name"],
        "prices": points,
        "source": "sqlite_cache" if history else stock.get("source", "seed_data"),
        "generated_at": datetime.now().isoformat(),
    }


def market_payload(section: str | None = None) -> dict[str, Any]:
    overview = get_market_overview()
    if section is None:
        return {
            **overview,
            "source": "market_intelligence",
            "generated_at": datetime.now().isoformat(),
        }
    return {
        "status": overview["status"],
        "stocks": overview.get(section, []),
        "source": "market_intelligence",
        "generated_at": datetime.now().isoformat(),
    }


def trending_stocks(limit: int = 6) -> list[dict[str, Any]]:
    overview = get_market_overview()
    seen = set()
    trending = []
    for stock in [*overview["top_gainers"], *overview["most_active"]]:
        ticker = stock.get("ticker")
        if ticker and ticker not in seen:
            seen.add(ticker)
            trending.append(stock)
        if len(trending) >= limit:
            break
    return trending

