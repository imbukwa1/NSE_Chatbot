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
        "full_name": "Favorite Test User",
        "email": f"favorite-test-{uuid4().hex[:12]}@example.com",
        "password": "StrongPass123",
    }
    client.post("/auth/register", json=payload)
    login = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


class FavoriteTests(unittest.TestCase):
    def test_add_list_and_remove_favorite(self):
        headers = auth_headers()

        created = client.post(
            "/users/me/favorites",
            json={"ticker": "SCOM"},
            headers=headers,
        )
        listed = client.get("/users/me/favorites", headers=headers)
        deleted = client.delete("/users/me/favorites/SCOM", headers=headers)

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["data"]["favorite"]["ticker"], "SCOM")
        self.assertEqual(listed.status_code, 200)
        self.assertGreaterEqual(len(listed.json()["data"]["favorites"]), 1)
        self.assertEqual(deleted.status_code, 200)

    def test_duplicate_favorite_prevention(self):
        headers = auth_headers()
        client.post("/users/me/favorites", json={"ticker": "KCB"}, headers=headers)
        duplicate = client.post(
            "/users/me/favorites",
            json={"ticker": "KCB"},
            headers=headers,
        )

        self.assertEqual(duplicate.status_code, 409)

    def test_invalid_ticker_rejected(self):
        headers = auth_headers()
        response = client.post(
            "/users/me/favorites",
            json={"ticker": "NOPE"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 404)

    def test_favorites_require_authentication(self):
        response = client.get("/users/me/favorites")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

