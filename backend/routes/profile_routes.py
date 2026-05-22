from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.user import User
from schemas.profile import ProfileResponse, RecentSearchCreate, RecentSearchResponse
from services.chat_service import api_success
from services.profile_service import (
    get_or_create_profile,
    get_recent_searches,
    save_recent_search,
)
from services.dashboard_service import recent_stock_views
from services.favorites_service import list_favorites
from services.watchlist_service import list_watchlist

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = get_or_create_profile(db, current_user)
    return api_success(
        "Profile retrieved successfully",
        {
            "profile": ProfileResponse(
                id=current_user.id,
                full_name=current_user.full_name,
                email=current_user.email,
                role=current_user.role,
                is_active=current_user.is_active,
                member_since=current_user.created_at,
                display_name=profile.display_name,
                investor_level=profile.investor_level,
                bio=profile.bio,
            ).model_dump(mode="json"),
            "favorites": list_favorites(db, current_user),
            "watchlist": list_watchlist(db, current_user),
            "recent_viewed_stocks": recent_stock_views(db, current_user),
            "recent_searches": [
                RecentSearchResponse.model_validate(item).model_dump(mode="json")
                for item in get_recent_searches(db, current_user, limit=10)
            ],
        },
    )


@router.get("/recent-searches")
def list_recent_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    searches = get_recent_searches(db, current_user)
    return api_success(
        "Recent searches retrieved successfully",
        {
            "recent_searches": [
                RecentSearchResponse.model_validate(item).model_dump(mode="json")
                for item in searches
            ]
        },
    )


@router.post("/recent-searches", status_code=status.HTTP_201_CREATED)
def create_recent_search(
    payload: RecentSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = save_recent_search(db, current_user, payload.search_query)
    return api_success(
        "Recent search saved successfully",
        {
            "recent_search": RecentSearchResponse.model_validate(item).model_dump(mode="json")
        },
    )
