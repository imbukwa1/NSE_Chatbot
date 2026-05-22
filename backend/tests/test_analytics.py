import sys
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

import database
from auth.auth import create_user
from main import app


client = TestClient(app)


def admin_headers() -> dict:
    email = f"analytics-admin-{uuid4().hex[:12]}@example.com"
    with database.SessionLocal() as db:
        create_user(
            db,
            full_name="Analytics Admin",
            email=email,
            password="StrongPass123",
            role="admin",
        )
    login = client.post("/auth/login", json={"email": email, "password": "StrongPass123"})
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


class AnalyticsTests(unittest.TestCase):
    def test_admin_analytics(self):
        response = client.get("/admin/analytics", headers=admin_headers())

        self.assertEqual(response.status_code, 200)
        analytics = response.json()["data"]["analytics"]
        self.assertIn("total_users", analytics)
        self.assertIn("total_conversations", analytics)
        self.assertIn("total_chatbot_requests", analytics)

    def test_analytics_requires_admin(self):
        response = client.get("/admin/analytics")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

