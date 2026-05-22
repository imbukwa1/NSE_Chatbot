from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.chat_service import api_success
from services.monitoring_service import database_status, integration_status, scraper_status, system_status

router = APIRouter(prefix="/system", tags=["System"])


def scheduler_is_running() -> bool:
    try:
        from main import scheduler

        return bool(scheduler.running)
    except Exception:
        return False


@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    return api_success(
        "System status retrieved successfully",
        {"system": system_status(db, scheduler_is_running())},
    )


@router.get("/scraper-status")
def get_system_scraper_status(db: Session = Depends(get_db)):
    return api_success(
        "Scraper status retrieved successfully",
        {"scraper": scraper_status(db, scheduler_is_running())},
    )


@router.get("/api-status")
def get_api_status(db: Session = Depends(get_db)):
    return api_success(
        "API status retrieved successfully",
        {
            "api": {
                "database": database_status(db),
                "integrations": integration_status(),
            }
        },
    )

