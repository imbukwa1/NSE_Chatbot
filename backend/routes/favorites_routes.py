from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.user import User
from schemas.favorite import FavoriteCreate
from services.chat_service import api_success
from services.favorites_service import add_favorite, list_favorites, remove_favorite

router = APIRouter(prefix="/users/me/favorites", tags=["Favorites"])


@router.get("")
def get_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return api_success(
        "Favorite stocks retrieved successfully",
        {"favorites": list_favorites(db, current_user)},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_favorite(
    payload: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    favorite = add_favorite(db, current_user, payload.ticker)
    return api_success("Favorite stock added successfully", {"favorite": favorite})


@router.delete("/{ticker}")
def delete_favorite(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    remove_favorite(db, current_user, ticker)
    return api_success("Favorite stock removed successfully", {"ticker": ticker.upper()})

