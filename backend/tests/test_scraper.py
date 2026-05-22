import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

import database
from main import app
from services.market_cache import EAT, get_cached_stock, get_market_status
from services.scraper import fetch_nse_market_snapshot, scrape_and_update_cache

client = TestClient(app)


class ScraperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

    def test_market_status_open_and_closed(self):
        open_time = EAT.localize(datetime(2026, 5, 19, 12, 0))
        closed_time = EAT.localize(datetime(2026, 5, 19, 16, 0))

        self.assertEqual(get_market_status(open_time)["status"], "OPEN")
        self.assertEqual(get_market_status(closed_time)["status"], "CLOSED")

    def test_snapshot_normalizes_scraped_data(self):
        with patch(
            "services.scraper.legacy_scrape_nse_data",
            return_value={
                "SCOM": {
                    "ticker": "SCOM",
                    "name": "Safaricom PLC",
                    "price": 18.45,
                    "change_pct": 2.1,
                    "volume": 1200000,
                    "source": "NSE",
                }
            },
        ):
            snapshot = fetch_nse_market_snapshot()

        self.assertEqual(snapshot[0]["ticker"], "SCOM")
        self.assertEqual(snapshot[0]["company_name"], "Safaricom PLC")
        self.assertEqual(snapshot[0]["change_percentage"], 2.1)
        self.assertIn("last_updated", snapshot[0])

    def test_scrape_updates_sqlite_cache(self):
        with patch(
            "services.scraper.legacy_scrape_nse_data",
            return_value={
                "SCOM": {
                    "ticker": "SCOM",
                    "name": "Safaricom PLC",
                    "price": 18.45,
                    "change_pct": 2.1,
                    "volume": 1200000,
                    "source": "NSE",
                }
            },
        ):
            result = scrape_and_update_cache("unit_test_snapshot")

        cached = get_cached_stock("SCOM")
        self.assertEqual(result["status"], "success")
        self.assertEqual(cached["price"], 18.45)
        self.assertEqual(cached["source"], "NSE")
        self.assertIn("last_updated", cached)

    def test_scrape_failure_uses_cached_or_seed_fallback(self):
        with patch("services.scraper.legacy_scrape_nse_data", side_effect=RuntimeError("network down")):
            result = scrape_and_update_cache("failure_test")

        self.assertEqual(result["status"], "fallback")
        self.assertTrue(result["stocks"])

    def test_market_status_endpoint(self):
        response = client.get("/market/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["status"]
        self.assertIn(payload["status"], {"OPEN", "CLOSED"})
        self.assertEqual(payload["hours"], "Mon-Fri, 09:00-15:00 EAT")


if __name__ == "__main__":
    unittest.main()
