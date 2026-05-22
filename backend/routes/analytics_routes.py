from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import get_current_admin
from database import get_db
from models.user import User
from services.analytics_service import admin_analytics
from services.chat_service import api_success

router = APIRouter(prefix="/admin", tags=["Admin Analytics"])


@router.get("/analytics")
def get_admin_analytics(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return api_success(
        "Admin analytics retrieved successfully",
        {"analytics": admin_analytics(db)},
    )

