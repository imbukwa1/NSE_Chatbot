import logging
from datetime import datetime
from typing import Any

from scraper import scrape_nse_data as legacy_scrape_nse_data

import database
from services.logging_service import log_scraper_run
from services.market_cache import EAT, get_all_cached_stocks, get_market_status

logger = logging.getLogger(__name__)


def _normalize_scraped_stock(
    ticker: str,
    stock: dict[str, Any],
    market_status: str,
    last_updated: str,
) -> dict[str, Any]:
    change = stock.get("change_percentage", stock.get("change_pct"))
    name = stock.get("company_name") or stock.get("name") or ticker
    return {
        "ticker": ticker.upper(),
        "name": name,
        "company_name": name,
        "price": stock.get("price"),
        "change_pct": change,
        "change_percentage": change,
        "volume": stock.get("volume"),
        "market_status": market_status,
        "source": stock.get("source") or "NSE",
        "last_updated": last_updated,
    }


def fetch_nse_market_snapshot() -> list[dict[str, Any]]:
    """Fetch one NSE snapshot and normalize it for SQLite caching."""
    now = datetime.now(EAT)
    status = get_market_status(now)["status"]
    last_updated = now.isoformat()
    scraped = legacy_scrape_nse_data()
    if not scraped:
        return []
    return [
        _normalize_scraped_stock(ticker, stock, status, last_updated)
        for ticker, stock in scraped.items()
        if ticker and stock
    ]


def scrape_and_update_cache(snapshot_label: str = "scheduled") -> dict[str, Any]:
    """
    Run a scheduled NSE scrape and persist the result.

    Failures never bubble into request handling; callers receive the latest cached
    data, or seed-backed cache data if the database is still empty.
    """
    logger.info("NSE scrape started: %s", snapshot_label)
    try:
        stocks = fetch_nse_market_snapshot()
        if not stocks:
            with database.SessionLocal() as db:
                log_scraper_run(db, "empty", 0, "Scrape returned no data")
            return {
                "status": "fallback",
                "snapshot": snapshot_label,
                "records_updated": 0,
                "stocks": get_all_cached_stocks(include_history=False),
            }

        records_updated = database.batch_insert_stocks(stocks)
        for stock in stocks:
            price = stock.get("price")
            if price is not None:
                database.record_price_history(stock["ticker"], price)

        with database.SessionLocal() as db:
            log_scraper_run(db, "success", records_updated)

        return {
            "status": "success",
            "snapshot": snapshot_label,
            "records_updated": records_updated,
            "stocks": stocks,
        }
    except Exception as exc:
        logger.exception("NSE scrape failed: %s", exc)
        with database.SessionLocal() as db:
            log_scraper_run(db, "failed", 0, str(exc))
        return {
            "status": "fallback",
            "snapshot": snapshot_label,
            "records_updated": 0,
            "error": str(exc),
            "stocks": get_all_cached_stocks(include_history=False),
        }
