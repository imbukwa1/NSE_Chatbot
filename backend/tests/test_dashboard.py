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
        "full_name": "Dashboard Test User",
        "email": f"dashboard-test-{uuid4().hex[:12]}@example.com",
        "password": "StrongPass123",
    }
    client.post("/auth/register", json=payload)
    login = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


class DashboardTests(unittest.TestCase):
    def test_dashboard_summary(self):
        headers = auth_headers()
        client.post("/users/me/favorites", json={"ticker": "SCOM"}, headers=headers)
        client.post(
            "/profile/recent-searches",
            json={"search_query": "Top gainers today"},
            headers=headers,
        )

        response = client.get("/dashboard/summary", headers=headers)

        self.assertEqual(response.status_code, 200)
        summary = response.json()["data"]["summary"]
        self.assertIn("market_status", summary)
        self.assertIn("top_gainers", summary)
        self.assertIn("favorites", summary)
        self.assertIn("recent_searches", summary)

    def test_dashboard_requires_authentication(self):
        response = client.get("/dashboard/summary")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

