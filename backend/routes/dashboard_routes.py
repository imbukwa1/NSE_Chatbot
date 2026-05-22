from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.user import User
from services.chat_service import api_success
from services.dashboard_service import dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return api_success(
        "Dashboard summary retrieved successfully",
        {"summary": dashboard_summary(db, current_user)},
    )

