import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

import database
from main import app, scheduler
from services.scheduler import register_market_scrape_jobs, scheduled_job_ids
from services.scraper import scrape_and_update_cache

client = TestClient(app)


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

    def test_database_file_and_cache_tables_exist(self):
        self.assertTrue((backend_path / "data" / "nse_stocks.db").exists())
        self.assertIsInstance(database.get_all_stocks(), list)

    def test_scraper_updates_cache_without_request_time_fetching(self):
        with patch(
            "services.scraper.legacy_scrape_nse_data",
            return_value={
                "KCB": {
                    "ticker": "KCB",
                    "name": "KCB Group PLC",
                    "price": 39.25,
                    "change_pct": 0.8,
                    "volume": 10000,
                    "source": "NSE",
                }
            },
        ):
            result = scrape_and_update_cache("integration_test")

        self.assertEqual(result["status"], "success")
        self.assertEqual(database.get_stock_by_ticker("KCB")["price"], 39.25)

    def test_scheduler_uses_fixed_daily_jobs(self):
        if scheduler.running:
            jobs = {job.id for job in scheduler.get_jobs()}
        else:
            scheduler.remove_all_jobs()
            register_market_scrape_jobs(scheduler)
            jobs = {job.id for job in scheduler.get_jobs()}

        self.assertEqual(jobs, set(scheduled_job_ids()))

    def test_fastapi_market_routes_are_registered(self):
        routes = {route.path for route in app.routes if hasattr(route, "path")}

        self.assertIn("/market/status", routes)
        self.assertIn("/market/overview", routes)
        self.assertIn("/stocks/{ticker}/chart", routes)

    def test_scraper_status_reports_daily_schedule(self):
        response = client.get("/scraper/status")

        self.assertEqual(response.status_code, 200)
        self.assertIn("09:00, 12:00, and 15:00 EAT", response.json()["scrape_schedule"])


if __name__ == "__main__":
    unittest.main()
