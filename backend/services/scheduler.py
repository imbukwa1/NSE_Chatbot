from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from services.scraper import scrape_and_update_cache

EAT = timezone("Africa/Nairobi")

SCHEDULED_SCRAPE_TIMES = (
    {"hour": 9, "minute": 0, "job_id": "nse_market_open", "label": "market_opening_snapshot"},
    {"hour": 12, "minute": 0, "job_id": "nse_midday_update", "label": "midday_market_update"},
    {"hour": 15, "minute": 0, "job_id": "nse_market_close", "label": "market_closing_snapshot"},
)


def run_market_open_scrape():
    return scrape_and_update_cache("market_opening_snapshot")


def run_midday_scrape():
    return scrape_and_update_cache("midday_market_update")


def run_market_close_scrape():
    return scrape_and_update_cache("market_closing_snapshot")


JOB_FUNCTIONS = {
    "market_opening_snapshot": run_market_open_scrape,
    "midday_market_update": run_midday_scrape,
    "market_closing_snapshot": run_market_close_scrape,
}


def register_market_scrape_jobs(scheduler) -> None:
    """Register the fixed daily NSE scrape schedule in East Africa Time."""
    for config in SCHEDULED_SCRAPE_TIMES:
        scheduler.add_job(
            JOB_FUNCTIONS[config["label"]],
            CronTrigger(
                hour=config["hour"],
                minute=config["minute"],
                timezone=EAT,
            ),
            id=config["job_id"],
            name=config["label"].replace("_", " ").title(),
            replace_existing=True,
        )


def scheduled_job_ids() -> list[str]:
    return [config["job_id"] for config in SCHEDULED_SCRAPE_TIMES]
