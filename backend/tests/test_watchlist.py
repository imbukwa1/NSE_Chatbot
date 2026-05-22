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
        "full_name": "Watchlist Test User",
        "email": f"watchlist-test-{uuid4().hex[:12]}@example.com",
        "password": "StrongPass123",
    }
    client.post("/auth/register", json=payload)
    login = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


class WatchlistTests(unittest.TestCase):
    def test_watchlist_crud(self):
        headers = auth_headers()
        created = client.post(
            "/users/me/watchlist",
            json={"ticker": "EQTY", "notes": "Watch banking performance."},
            headers=headers,
        )
        updated = client.put(
            "/users/me/watchlist/EQTY",
            json={"notes": "Updated notes"},
            headers=headers,
        )
        listed = client.get("/users/me/watchlist", headers=headers)
        deleted = client.delete("/users/me/watchlist/EQTY", headers=headers)

        self.assertEqual(created.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["watchlist_item"]["notes"], "Updated notes")
        self.assertEqual(listed.status_code, 200)
        self.assertGreaterEqual(len(listed.json()["data"]["watchlist"]), 1)
        self.assertEqual(deleted.status_code, 200)

    def test_duplicate_watchlist_prevention(self):
        headers = auth_headers()
        client.post("/users/me/watchlist", json={"ticker": "SCOM"}, headers=headers)
        duplicate = client.post(
            "/users/me/watchlist",
            json={"ticker": "SCOM"},
            headers=headers,
        )

        self.assertEqual(duplicate.status_code, 409)

    def test_missing_watchlist_item(self):
        headers = auth_headers()
        response = client.put(
            "/users/me/watchlist/KCB",
            json={"notes": "No row yet"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 404)

    def test_watchlist_requires_authentication(self):
        response = client.get("/users/me/watchlist")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

