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
        "full_name": "Profile Test User",
        "email": f"profile-test-{uuid4().hex[:12]}@example.com",
        "password": "StrongPass123",
    }
    client.post("/auth/register", json=payload)
    login = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


class ProfileTests(unittest.TestCase):
    def test_get_profile(self):
        headers = auth_headers()

        response = client.get("/profile/me", headers=headers)

        self.assertEqual(response.status_code, 200)
        profile = response.json()["data"]["profile"]
        self.assertEqual(profile["investor_level"], "Investor Explorer")
        self.assertEqual(profile["role"], "user")

    def test_recent_search_create_and_list(self):
        headers = auth_headers()
        created = client.post(
            "/profile/recent-searches",
            json={"search_query": "Compare KCB and Equity"},
            headers=headers,
        )
        listed = client.get("/profile/recent-searches", headers=headers)

        self.assertEqual(created.status_code, 201)
        self.assertEqual(listed.status_code, 200)
        searches = listed.json()["data"]["recent_searches"]
        self.assertGreaterEqual(len(searches), 1)
        self.assertEqual(searches[0]["search_query"], "Compare KCB and Equity")

    def test_recent_searches_are_limited(self):
        headers = auth_headers()
        for index in range(25):
            client.post(
                "/profile/recent-searches",
                json={"search_query": f"Search {index}"},
                headers=headers,
            )

        listed = client.get("/profile/recent-searches", headers=headers)

        self.assertEqual(listed.status_code, 200)
        self.assertLessEqual(len(listed.json()["data"]["recent_searches"]), 20)

    def test_profile_routes_require_authentication(self):
        response = client.get("/profile/me")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

