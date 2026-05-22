from sqlalchemy.orm import Session

from models.admin_log import AdminLog
from models.scraper_log import ScraperLog
from models.system_log import SystemLog


def log_admin_action(
    db: Session,
    admin_user_id: int,
    action: str,
    target: str | None = None,
) -> AdminLog:
    entry = AdminLog(admin_user_id=admin_user_id, action=action, target=target)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def log_scraper_run(
    db: Session,
    status: str,
    records_updated: int = 0,
    error_message: str | None = None,
) -> ScraperLog:
    entry = ScraperLog(
        status=status,
        records_updated=records_updated,
        error_message=error_message,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def log_system_event(db: Session, event_type: str, description: str) -> SystemLog:
    entry = SystemLog(event_type=event_type, description=description)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

