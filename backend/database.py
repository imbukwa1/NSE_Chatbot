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

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Database path
DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "nse_stocks.db"
print("DATABASE PATH:", DB_PATH.resolve())
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_db_exists():
    """Create database file if it doesn't exist."""
    DB_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    """FastAPI dependency for SQLAlchemy-backed application models."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_auth_db():
    """Create SQLAlchemy-managed application tables."""
    ensure_db_exists()
    # Import models here so SQLAlchemy registers them before create_all().
    from models.user import User  # noqa: F401
    from models.chat import ChatMessage, ChatSession  # noqa: F401
    from models.favorite_stock import FavoriteStock  # noqa: F401
    from models.admin_log import AdminLog  # noqa: F401
    from models.profile import UserProfile  # noqa: F401
    from models.knowledge_base import KnowledgeBaseEntry  # noqa: F401
    from models.recent_search import RecentSearch  # noqa: F401
    from models.scraper_log import ScraperLog  # noqa: F401
    from models.stock_view import StockView  # noqa: F401
    from models.system_log import SystemLog  # noqa: F401
    from models.watchlist import Watchlist  # noqa: F401

    Base.metadata.create_all(bind=engine)


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
    init_auth_db()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Keep the SQLAlchemy-managed knowledge base table compatible with
        # existing local SQLite files. create_all() creates new tables, but it
        # does not add columns to tables that already exist.
        kb_columns = {
            row["name"]
            for row in cursor.execute("PRAGMA table_info(knowledge_base_entries)").fetchall()
        }
        kb_migrations = {
            "source_id": "ALTER TABLE knowledge_base_entries ADD COLUMN source_id TEXT",
            "slug": "ALTER TABLE knowledge_base_entries ADD COLUMN slug TEXT",
            "subcategory": "ALTER TABLE knowledge_base_entries ADD COLUMN subcategory TEXT",
            "aliases": "ALTER TABLE knowledge_base_entries ADD COLUMN aliases TEXT",
            "answer_markdown": "ALTER TABLE knowledge_base_entries ADD COLUMN answer_markdown TEXT",
            "keywords": "ALTER TABLE knowledge_base_entries ADD COLUMN keywords TEXT",
            "difficulty": "ALTER TABLE knowledge_base_entries ADD COLUMN difficulty TEXT",
            "related_questions": "ALTER TABLE knowledge_base_entries ADD COLUMN related_questions TEXT",
            "embedding_model": "ALTER TABLE knowledge_base_entries ADD COLUMN embedding_model TEXT",
            "embedding_content_hash": "ALTER TABLE knowledge_base_entries ADD COLUMN embedding_content_hash TEXT",
            "pinecone_vector_id": "ALTER TABLE knowledge_base_entries ADD COLUMN pinecone_vector_id TEXT",
            "pinecone_synced_at": "ALTER TABLE knowledge_base_entries ADD COLUMN pinecone_synced_at TIMESTAMP",
        }
        for column_name, statement in kb_migrations.items():
            if column_name not in kb_columns:
                cursor.execute(statement)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kb_source_id
            ON knowledge_base_entries(source_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kb_slug
            ON knowledge_base_entries(slug)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kb_embedding_content_hash
            ON knowledge_base_entries(embedding_content_hash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kb_pinecone_vector_id
            ON knowledge_base_entries(pinecone_vector_id)
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                files_scanned INTEGER NOT NULL DEFAULT 0,
                rows_seen INTEGER NOT NULL DEFAULT 0,
                imported_count INTEGER NOT NULL DEFAULT 0,
                skipped_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'success'
            )
        """)

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
                market_status TEXT,
                source TEXT,
                last_updated TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Lightweight migrations for existing SQLite databases.
        existing_columns = {
            row["name"]
            for row in cursor.execute("PRAGMA table_info(stocks)").fetchall()
        }
        if "market_status" not in existing_columns:
            cursor.execute("ALTER TABLE stocks ADD COLUMN market_status TEXT")
        if "last_updated" not in existing_columns:
            cursor.execute("ALTER TABLE stocks ADD COLUMN last_updated TIMESTAMP")

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
                (ticker, name, price, change_pct, volume, pe_ratio, dividend_yield,
                 market_status, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    name = excluded.name,
                    price = excluded.price,
                    change_pct = excluded.change_pct,
                    volume = excluded.volume,
                    pe_ratio = excluded.pe_ratio,
                    dividend_yield = excluded.dividend_yield,
                    market_status = excluded.market_status,
                    source = excluded.source,
                    last_updated = excluded.last_updated,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                ticker,
                stock_data.get("name", ""),
                stock_data.get("price"),
                stock_data.get("change_pct"),
                stock_data.get("volume"),
                stock_data.get("pe_ratio"),
                stock_data.get("dividend_yield"),
                stock_data.get("market_status"),
                stock_data.get("source", "unknown"),
                stock_data.get("last_updated") or datetime.now().isoformat(),
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
                       dividend_yield, market_status, source, last_updated, updated_at
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
                       dividend_yield, market_status, source, last_updated, updated_at
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
