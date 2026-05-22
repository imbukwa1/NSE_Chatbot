from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.user import User
from schemas.watchlist import WatchlistCreate, WatchlistUpdate
from services.chat_service import api_success
from services.watchlist_service import (
    add_watchlist_item,
    list_watchlist,
    remove_watchlist_item,
    update_watchlist_item,
)

router = APIRouter(prefix="/users/me/watchlist", tags=["Watchlist"])


@router.get("")
def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return api_success(
        "Watchlist retrieved successfully",
        {"watchlist": list_watchlist(db, current_user)},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_watchlist_item(
    payload: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = add_watchlist_item(db, current_user, payload.ticker, payload.notes)
    return api_success("Watchlist item added successfully", {"watchlist_item": item})


@router.put("/{ticker}")
def edit_watchlist_item(
    ticker: str,
    payload: WatchlistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = update_watchlist_item(db, current_user, ticker, payload.notes)
    return api_success("Watchlist item updated successfully", {"watchlist_item": item})


@router.delete("/{ticker}")
def delete_watchlist_item(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    remove_watchlist_item(db, current_user, ticker)
    return api_success("Watchlist item removed successfully", {"ticker": ticker.upper()})

