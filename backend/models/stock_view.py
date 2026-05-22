from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base


class StockView(Base):
    __tablename__ = "stock_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    viewed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

