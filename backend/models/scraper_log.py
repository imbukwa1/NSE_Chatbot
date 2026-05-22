from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class ScraperLog(Base):
    __tablename__ = "scraper_logs"

    id = Column(Integer, primary_key=True, index=True)
    scrape_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    status = Column(String(40), nullable=False, index=True)
    records_updated = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

