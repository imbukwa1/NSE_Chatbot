import os
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

import database
from models.scraper_log import ScraperLog


def database_status(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "sqlite"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def integration_status() -> dict:
    return {
        "featherless": "configured" if os.getenv("FEATHERLESS_API_KEY") else "missing_key",
        "pinecone": "configured" if os.getenv("PINECONE_API_KEY") else "missing_key",
        "newsapi": "configured" if os.getenv("NEWSAPI_KEY") else "missing_key",
    }


def scraper_status(db: Session, scheduler_running: bool) -> dict:
    last_log = db.query(ScraperLog).order_by(ScraperLog.scrape_time.desc()).first()
    return {
        "scheduler_running": scheduler_running,
        "schedule": "09:00, 12:00, and 15:00 EAT",
        "last_scrape": last_log.scrape_time.isoformat() if last_log else database.get_last_update_time(),
        "last_status": last_log.status if last_log else "unknown",
        "records_updated": last_log.records_updated if last_log else 0,
        "generated_at": datetime.now().isoformat(),
    }


def system_status(db: Session, scheduler_running: bool) -> dict:
    return {
        "chatbot": "online",
        "database": database_status(db),
        "scraper": scraper_status(db, scheduler_running),
        "integrations": integration_status(),
        "generated_at": datetime.now().isoformat(),
    }
