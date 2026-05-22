import sys
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

from main import app


client = TestClient(app)


def auth_headers() -> dict:
    payload = {
        "full_name": "Market Test User",
        "email": f"market-test-{uuid4().hex[:12]}@example.com",
        "password": "StrongPass123",
    }
    client.post("/auth/register", json=payload)
    login = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


class MarketTests(unittest.TestCase):
    def test_stock_search(self):
        response = client.get("/stocks/search", params={"q": "Saf"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["results"])

    def test_chart_endpoint(self):
        response = client.get("/stocks/SCOM/chart", headers=auth_headers())

        self.assertEqual(response.status_code, 200)
        chart = response.json()["data"]["chart"]
        self.assertEqual(chart["ticker"], "SCOM")
        self.assertIn("prices", chart)

    def test_market_overview_endpoints(self):
        for path in [
            "/market/overview",
            "/market/top-gainers",
            "/market/top-losers",
            "/market/most-active",
            "/market/trending",
        ]:
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertTrue(response.json()["success"])


if __name__ == "__main__":
    unittest.main()

