import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

from main import app


client = TestClient(app)


class MonitoringTests(unittest.TestCase):
    def test_system_status(self):
        response = client.get("/system/status")

        self.assertEqual(response.status_code, 200)
        system = response.json()["data"]["system"]
        self.assertIn("database", system)
        self.assertIn("scraper", system)
        self.assertIn("integrations", system)

    def test_scraper_status(self):
        response = client.get("/system/scraper-status")

        self.assertEqual(response.status_code, 200)
        self.assertIn("scraper", response.json()["data"])

    def test_api_status(self):
        response = client.get("/system/api-status")

        self.assertEqual(response.status_code, 200)
        self.assertIn("api", response.json()["data"])


if __name__ == "__main__":
    unittest.main()

