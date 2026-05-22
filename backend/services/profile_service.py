from sqlalchemy.orm import Session

from models.profile import UserProfile
from models.recent_search import RecentSearch
from models.user import User


def get_or_create_profile(db: Session, user: User) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile:
        return profile

    profile = UserProfile(
        user_id=user.id,
        display_name=user.full_name,
        investor_level="Investor Explorer",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def save_recent_search(
    db: Session,
    user: User,
    search_query: str,
    limit: int = 20,
) -> RecentSearch:
    recent = RecentSearch(user_id=user.id, search_query=search_query.strip())
    db.add(recent)
    db.commit()
    db.refresh(recent)

    old_items = (
        db.query(RecentSearch)
        .filter(RecentSearch.user_id == user.id)
        .order_by(RecentSearch.created_at.desc())
        .offset(limit)
        .all()
    )
    for item in old_items:
        db.delete(item)
    db.commit()
    return recent


def get_recent_searches(
    db: Session,
    user: User,
    limit: int = 20,
) -> list[RecentSearch]:
    return (
        db.query(RecentSearch)
        .filter(RecentSearch.user_id == user.id)
        .order_by(RecentSearch.created_at.desc())
        .limit(limit)
        .all()
    )

