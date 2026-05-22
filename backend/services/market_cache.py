import json
from datetime import datetime, time
from pathlib import Path
from typing import Any

from pytz import timezone

import database

EAT = timezone("Africa/Nairobi")
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "nse_seed.json"


def _load_seed_data() -> dict[str, dict[str, Any]]:
    try:
        with open(SEED_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


_SEED_CACHE = _load_seed_data()


def get_market_status(now: datetime | None = None) -> dict[str, Any]:
    current = now.astimezone(EAT) if now else datetime.now(EAT)
    open_time = time(9, 0)
    close_time = time(15, 0)
    is_open = current.weekday() < 5 and open_time <= current.time() <= close_time
    return {
        "is_open": is_open,
        "status": "OPEN" if is_open else "CLOSED",
        "label": "Market Open" if is_open else "Market Closed",
        "time_eat": current.isoformat(),
        "hours": "Mon-Fri, 09:00-15:00 EAT",
    }


def _seed_payload(ticker: str, include_history: bool = False) -> dict[str, Any] | None:
    record = _SEED_CACHE.get(ticker.upper())
    if not record:
        return None
    return {
        "ticker": ticker.upper(),
        "name": record.get("name", ticker.upper()),
        "company_name": record.get("name", ticker.upper()),
        "price": record.get("price"),
        "history": record.get("history", []) if include_history else [],
        "pe_ratio": record.get("pe_ratio"),
        "dividend_yield": record.get("dividend_yield"),
        "change_pct": record.get("change_pct"),
        "change_percentage": record.get("change_pct"),
        "volume": record.get("volume"),
        "market_status": get_market_status()["status"],
        "source": "seed_data",
        "last_updated": None,
    }


def _normalize_cached_stock(
    stock: dict[str, Any],
    include_history: bool = False,
) -> dict[str, Any]:
    ticker = str(stock.get("ticker", "")).upper()
    last_updated = stock.get("last_updated") or stock.get("updated_at")
    payload = {
        "ticker": ticker,
        "name": stock.get("name", ticker),
        "company_name": stock.get("name", ticker),
        "price": stock.get("price"),
        "history": [],
        "pe_ratio": stock.get("pe_ratio"),
        "dividend_yield": stock.get("dividend_yield"),
        "change_pct": stock.get("change_pct"),
        "change_percentage": stock.get("change_pct"),
        "volume": stock.get("volume"),
        "market_status": stock.get("market_status") or get_market_status()["status"],
        "source": stock.get("source") or "sqlite_cache",
        "last_updated": last_updated,
        "updated_at": stock.get("updated_at"),
    }
    if include_history:
        history = database.get_price_history(ticker, days=365)
        payload["history"] = [
            {"date": item.get("recorded_at"), "price": item.get("price")}
            for item in reversed(history)
            if item.get("price") is not None
        ]
    return payload


def get_cached_stock(
    ticker: str,
    include_history: bool = False,
    allow_seed_fallback: bool = True,
) -> dict[str, Any] | None:
    normalized = ticker.strip().upper()
    cached = database.get_stock_by_ticker(normalized)
    if cached:
        payload = _normalize_cached_stock(cached, include_history=include_history)
        if include_history and not payload.get("history"):
            seed = _seed_payload(normalized, include_history=True)
            if seed:
                payload["history"] = seed.get("history", [])
        return payload
    if allow_seed_fallback:
        return _seed_payload(normalized, include_history=include_history)
    return None


def get_all_cached_stocks(
    include_history: bool = False,
    allow_seed_fallback: bool = True,
) -> list[dict[str, Any]]:
    cached = database.get_all_stocks()
    if cached:
        return [
            _normalize_cached_stock(stock, include_history=include_history)
            for stock in cached
        ]
    if not allow_seed_fallback:
        return []
    return [
        stock
        for ticker in sorted(_SEED_CACHE)
        if (stock := _seed_payload(ticker, include_history=include_history))
    ]


def format_stock_response(stock: dict[str, Any]) -> str:
    change = stock.get("change_pct")
    direction = "flat"
    if isinstance(change, (int, float)) and change > 0:
        direction = f"up {change:.2f}%"
    elif isinstance(change, (int, float)) and change < 0:
        direction = f"down {abs(change):.2f}%"

    updated = stock.get("last_updated") or "latest cached snapshot"
    price = stock.get("price")
    price_text = f"KES {price:.2f}" if isinstance(price, (int, float)) else "unavailable"
    return (
        f"{stock.get('name', stock.get('ticker'))} ({stock.get('ticker')}) is currently "
        f"trading at {price_text}, {direction} today.\n\n"
        f"Last updated: {updated}\n"
        f"Source: {stock.get('source', 'sqlite_cache')}\n\n"
        "This is not financial advice."
    )
