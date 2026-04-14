from datetime import date, timedelta
from typing import Any
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from services.data_fetcher import NSEDataFetcher, TICKER_ALIASES


_fetcher = NSEDataFetcher()
_seed_cache: dict[str, dict[str, Any]] | None = None
_executor = ThreadPoolExecutor(max_workers=4)

# Pre-load seed data at import time
def _load_seed_at_startup() -> dict[str, dict[str, Any]]:
    seed_path = Path(__file__).resolve().parent.parent / "data" / "nse_seed.json"
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_seed_cache = _load_seed_at_startup()


def load_stock_data() -> dict[str, dict[str, Any]]:
    # Build lookup from seed cache seed cache - NEVER call yfinance here, it will hang
    seed_records = _seed_cache
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


def get_stock_data(ticker: str, include_history: bool = False) -> dict[str, Any] | None:
    # Try to fetch from yfinance with 3-second hard timeout
    stock = None
    try:
        future = _executor.submit(_fetcher.get_price, ticker)
        stock = future.result(timeout=3)
    except (FuturesTimeoutError, Exception):
        # Timeout or error — use seed data
        stock = None

    if not stock:
        # Fall back to seed data immediately
        seed_record = _seed_cache.get(ticker)
        if seed_record:
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
        return None

    price = stock.get("price")

    # Use seed data for missing fields
    seed_record = _seed_cache.get(ticker, {})
    pe_ratio = stock.get("pe_ratio") or seed_record.get("pe_ratio")
    dividend_yield = stock.get("dividend_yield") or seed_record.get("dividend_yield")
    history = seed_record.get("history", []) if include_history else []

    return {
        "ticker": stock["ticker"],
        "name": stock.get("name", stock["ticker"]),
        "price": price,
        "history": history,
        "pe_ratio": pe_ratio,
        "dividend_yield": dividend_yield,
        "change_pct": stock.get("change_pct"),
        "volume": stock.get("volume"),
        "source": stock.get("source", "yfinance"),
    }
