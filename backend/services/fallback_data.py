from __future__ import annotations

from datetime import date, timedelta
from typing import Any


FALLBACK_STOCKS: dict[str, dict[str, Any]] = {
    "SCOM": {
        "name": "Safaricom",
        "price": 22.8,
        "pe_ratio": 14.2,
        "dividend_yield": 0.052,
    },
    "KQ": {
        "name": "Kenya Airways",
        "price": 6.2,
        "pe_ratio": None,
        "dividend_yield": 0.0,
    },
    "EQTY": {
        "name": "Equity Group Holdings",
        "price": 47.5,
        "pe_ratio": 6.8,
        "dividend_yield": 0.091,
    },
    "EABL": {
        "name": "East African Breweries",
        "price": 185.0,
        "pe_ratio": 18.4,
        "dividend_yield": 0.042,
    },
}


def _fallback_history(price: float) -> list[dict[str, Any]]:
    start_date = date.today() - timedelta(days=29)
    history = []
    for offset in range(30):
        drift = 1 + ((offset - 14) * 0.0015)
        history.append(
            {
                "date": (start_date + timedelta(days=offset)).isoformat(),
                "price": round(price * drift, 2),
            }
        )
    return history


def get_fallback_stock_data(ticker: str, include_history: bool = False) -> dict[str, Any] | None:
    normalized_ticker = ticker.upper().strip()
    fallback = FALLBACK_STOCKS.get(normalized_ticker)
    if not fallback:
        return None

    price = float(fallback["price"])
    return {
        "ticker": normalized_ticker,
        "name": fallback["name"],
        "symbol": normalized_ticker,
        "price": price,
        "history": _fallback_history(price) if include_history else [],
        "pe_ratio": fallback.get("pe_ratio"),
        "dividend_yield": fallback.get("dividend_yield"),
        "source": "fallback",
    }
