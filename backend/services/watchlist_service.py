from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.user import User
from models.watchlist import Watchlist
from services.market_service import require_stock, stock_snapshot


def list_watchlist(db: Session, user: User) -> list[dict]:
    items = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user.id)
        .order_by(Watchlist.created_at.desc())
        .all()
    )
    return [
        {
            "id": item.id,
            "user_id": item.user_id,
            "ticker": item.ticker,
            "notes": item.notes,
            "created_at": item.created_at,
            "stock": stock_snapshot(item.ticker),
        }
        for item in items
    ]


def add_watchlist_item(
    db: Session,
    user: User,
    ticker: str,
    notes: str | None = None,
) -> dict:
    stock = require_stock(ticker)
    item = Watchlist(user_id=user.id, ticker=stock["ticker"], notes=notes)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{stock['ticker']} is already in the watchlist.",
        ) from exc
    db.refresh(item)
    return {
        "id": item.id,
        "user_id": item.user_id,
        "ticker": item.ticker,
        "notes": item.notes,
        "created_at": item.created_at,
        "stock": stock,
    }


def update_watchlist_item(
    db: Session,
    user: User,
    ticker: str,
    notes: str | None,
) -> dict:
    normalized = ticker.strip().upper()
    item = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user.id, Watchlist.ticker == normalized)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{normalized} is not in the watchlist.",
        )
    item.notes = notes
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "user_id": item.user_id,
        "ticker": item.ticker,
        "notes": item.notes,
        "created_at": item.created_at,
        "stock": stock_snapshot(item.ticker),
    }


def remove_watchlist_item(db: Session, user: User, ticker: str) -> None:
    normalized = ticker.strip().upper()
    item = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user.id, Watchlist.ticker == normalized)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{normalized} is not in the watchlist.",
        )
    db.delete(item)
    db.commit()

