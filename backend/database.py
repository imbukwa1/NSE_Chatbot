"""
SQLite Database Handler for NSE Stocks
Manages persistent storage of stock data with timestamps.
"""

import logging
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Database path
DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "nse_stocks.db"


def ensure_db_exists():
    """Create database file if it doesn't exist."""
    DB_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Return rows as dicts
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database tables."""
    ensure_db_exists()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Create stocks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                price REAL,
                change_pct REAL,
                volume INTEGER,
                pe_ratio REAL,
                dividend_yield REAL,
                source TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for faster ticker lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticker ON stocks(ticker)
        """)

        # Create history table for price tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                price REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticker) REFERENCES stocks(ticker)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticker_date ON price_history(ticker, recorded_at)
        """)

        conn.commit()
        logger.info("Database initialized successfully")


def insert_or_update_stock(stock_data: dict[str, Any]) -> bool:
    """
    Insert or update a stock record.

    Args:
        stock_data: Dictionary with ticker, name, price, change_pct, volume, etc.

    Returns:
        True if successful, False otherwise
    """
    try:
        ticker = stock_data.get("ticker")

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO stocks
                (ticker, name, price, change_pct, volume, pe_ratio, dividend_yield, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    name = excluded.name,
                    price = excluded.price,
                    change_pct = excluded.change_pct,
                    volume = excluded.volume,
                    pe_ratio = excluded.pe_ratio,
                    dividend_yield = excluded.dividend_yield,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                ticker,
                stock_data.get("name", ""),
                stock_data.get("price"),
                stock_data.get("change_pct"),
                stock_data.get("volume"),
                stock_data.get("pe_ratio"),
                stock_data.get("dividend_yield"),
                stock_data.get("source", "unknown"),
            ))

            conn.commit()
            return True

    except Exception as e:
        logger.error(f"Failed to insert/update stock {ticker}: {e}")
        return False


def batch_insert_stocks(stocks_list: list[dict[str, Any]]) -> int:
    """
    Insert or update multiple stocks at once.

    Args:
        stocks_list: List of stock dictionaries

    Returns:
        Number of stocks successfully inserted/updated
    """
    count = 0
    for stock in stocks_list:
        if insert_or_update_stock(stock):
            count += 1

    logger.info(f"Batch inserted/updated {count} stocks")
    return count


def get_all_stocks() -> list[dict[str, Any]]:
    """Get all stocks from database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ticker, name, price, change_pct, volume, pe_ratio,
                       dividend_yield, source, updated_at
                FROM stocks
                ORDER BY ticker
            """)

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Failed to get all stocks: {e}")
        return []


def get_stock_by_ticker(ticker: str) -> dict[str, Any] | None:
    """Get a specific stock by ticker."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ticker, name, price, change_pct, volume, pe_ratio,
                       dividend_yield, source, updated_at
                FROM stocks
                WHERE ticker = ?
            """, (ticker.upper(),))

            row = cursor.fetchone()
            return dict(row) if row else None

    except Exception as e:
        logger.error(f"Failed to get stock {ticker}: {e}")
        return None


def record_price_history(ticker: str, price: float) -> bool:
    """Record price in history table for tracking."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_history (ticker, price)
                VALUES (?, ?)
            """, (ticker.upper(), price))

            conn.commit()
            return True

    except Exception as e:
        logger.error(f"Failed to record price history for {ticker}: {e}")
        return False


def get_price_history(ticker: str, days: int = 30) -> list[dict[str, Any]]:
    """Get price history for a stock (last N days)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ticker, price, recorded_at
                FROM price_history
                WHERE ticker = ? AND recorded_at >= datetime('now', '-' || ? || ' days')
                ORDER BY recorded_at DESC
                LIMIT 100
            """, (ticker.upper(), days))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Failed to get price history for {ticker}: {e}")
        return []


def get_last_update_time() -> str | None:
    """Get timestamp of the last database update."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(updated_at) as last_update
                FROM stocks
            """)

            row = cursor.fetchone()
            return row["last_update"] if row and row["last_update"] else None

    except Exception as e:
        logger.error(f"Failed to get last update time: {e}")
        return None


def clear_old_history(days: int = 90):
    """Clear price history older than N days."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM price_history
                WHERE recorded_at < datetime('now', '-' || ? || ' days')
            """, (days,))

            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Deleted {deleted} old price history records")
            return deleted

    except Exception as e:
        logger.error(f"Failed to clear old history: {e}")
        return 0
