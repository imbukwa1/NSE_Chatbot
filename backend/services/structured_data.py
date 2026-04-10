from datetime import date, timedelta
from typing import Any

from services.data_fetcher import NSEDataFetcher, TICKER_ALIASES


_fetcher = NSEDataFetcher()


def load_stock_data() -> dict[str, dict[str, Any]]:
    seed_records = {
        ticker: _fetcher.get_price(ticker)
        for ticker in _fetcher.get_all_seed_tickers()
    }
    return {
        ticker: {
            "name": record.get("name", ticker) if record else ticker,
            "aliases": [
                alias.lower()
                for alias, resolved_ticker in TICKER_ALIASES.items()
                if resolved_ticker == ticker
            ],
        }
        for ticker, record in seed_records.items()
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


def get_stock_data(ticker: str, include_history: bool = False) -> dict[str, Any] | None:
    stock = _fetcher.get_price(ticker)
    if not stock:
        return None

    price = stock.get("price")
    return {
        "ticker": stock["ticker"],
        "name": stock.get("name", stock["ticker"]),
        "price": price,
        "history": _fallback_history(float(price)) if include_history and price else [],
        "pe_ratio": stock.get("pe_ratio"),
        "dividend_yield": stock.get("dividend_yield"),
        "change_pct": stock.get("change_pct"),
        "volume": stock.get("volume"),
        "source": stock.get("source", "seed_data"),
    }
