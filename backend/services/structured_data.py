import json
from pathlib import Path
from typing import Any

from services.data_fetcher import NSEDataFetcher, TICKER_ALIASES
from services.market_cache import get_all_cached_stocks, get_cached_stock

_fetcher = NSEDataFetcher()
_seed_cache: dict[str, dict[str, Any]] | None = None


def _load_seed_at_startup() -> dict[str, dict[str, Any]]:
    seed_path = Path(__file__).resolve().parent.parent / "data" / "nse_seed.json"
    try:
        with open(seed_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


_seed_cache = _load_seed_at_startup()


def load_stock_data() -> dict[str, dict[str, Any]]:
    return {
        ticker: {
            "name": record.get("name", ticker) if record else ticker,
            "aliases": [
                alias.lower()
                for alias, resolved_ticker in TICKER_ALIASES.items()
                if resolved_ticker == ticker
            ],
        }
        for ticker, record in _seed_cache.items()
    }


def _seed_payload(ticker: str, include_history: bool = False) -> dict[str, Any] | None:
    seed_record = _seed_cache.get(ticker)
    if not seed_record:
        return None
    return {
        "ticker": ticker,
        "name": seed_record.get("name", ticker),
        "price": seed_record.get("price"),
        "history": seed_record.get("history", []) if include_history else [],
        "pe_ratio": seed_record.get("pe_ratio"),
        "dividend_yield": seed_record.get("dividend_yield"),
        "change_pct": seed_record.get("change_pct"),
        "volume": seed_record.get("volume"),
        "source": "seed_data",
    }


def get_all_stock_data(include_history: bool = False) -> list[dict[str, Any]]:
    """Return SQLite-cached market data, with local seed data as fallback."""
    return get_all_cached_stocks(include_history=include_history)


def get_stock_data(ticker: str, include_history: bool = False) -> dict[str, Any] | None:
    """Resolve a ticker and return cached stock data without request-time scraping."""
    resolved = _fetcher.resolve_ticker(ticker)
    return get_cached_stock(resolved, include_history=include_history)
