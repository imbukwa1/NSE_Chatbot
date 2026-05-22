from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.favorite_stock import FavoriteStock
from models.user import User
from services.market_service import require_stock, stock_snapshot


def list_favorites(db: Session, user: User) -> list[dict]:
    favorites = (
        db.query(FavoriteStock)
        .filter(FavoriteStock.user_id == user.id)
        .order_by(FavoriteStock.created_at.desc())
        .all()
    )
    return [
        {
            "id": item.id,
            "user_id": item.user_id,
            "ticker": item.ticker,
            "created_at": item.created_at,
            "stock": stock_snapshot(item.ticker),
        }
        for item in favorites
    ]


def add_favorite(db: Session, user: User, ticker: str) -> dict:
    stock = require_stock(ticker)
    favorite = FavoriteStock(user_id=user.id, ticker=stock["ticker"])
    db.add(favorite)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{stock['ticker']} is already in favorites.",
        ) from exc
    db.refresh(favorite)
    return {
        "id": favorite.id,
        "user_id": favorite.user_id,
        "ticker": favorite.ticker,
        "created_at": favorite.created_at,
        "stock": stock,
    }


def remove_favorite(db: Session, user: User, ticker: str) -> None:
    normalized = ticker.strip().upper()
    favorite = (
        db.query(FavoriteStock)
        .filter(FavoriteStock.user_id == user.id, FavoriteStock.ticker == normalized)
        .first()
    )
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{normalized} is not in favorites.",
        )
    db.delete(favorite)
    db.commit()

