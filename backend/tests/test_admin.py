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


def make_admin_headers() -> dict:
    email = f"admin-test-{uuid4().hex[:12]}@example.com"
    with database.SessionLocal() as db:
        create_user(
            db,
            full_name="Admin Test User",
            email=email,
            password="StrongPass123",
            role="admin",
        )
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def make_user() -> dict:
    payload = {
        "full_name": "Managed User",
        "email": f"managed-user-{uuid4().hex[:12]}@example.com",
        "password": "StrongPass123",
    }
    client.post("/auth/register", json=payload)
    return payload


class AdminTests(unittest.TestCase):
    def test_admin_routes_reject_normal_user(self):
        user = make_user()
        login = client.post(
            "/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        response = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {login.json()['data']['access_token']}"},
        )

        self.assertEqual(response.status_code, 403)

    def test_list_users_and_update_status_role(self):
        headers = make_admin_headers()
        user = make_user()
        users = client.get("/admin/users", headers=headers)
        managed = next(
            item for item in users.json()["data"]["users"] if item["email"] == user["email"]
        )

        status_response = client.patch(
            f"/admin/users/{managed['id']}/status",
            json={"is_active": False},
            headers=headers,
        )
        role_response = client.patch(
            f"/admin/users/{managed['id']}/role",
            json={"role": "guest"},
            headers=headers,
        )

        self.assertEqual(users.status_code, 200)
        self.assertEqual(status_response.status_code, 200)
        self.assertFalse(status_response.json()["data"]["user"]["is_active"])
        self.assertEqual(role_response.status_code, 200)
        self.assertEqual(role_response.json()["data"]["user"]["role"], "guest")

    def test_delete_user(self):
        headers = make_admin_headers()
        user = make_user()
        users = client.get("/admin/users", headers=headers).json()["data"]["users"]
        managed = next(item for item in users if item["email"] == user["email"])

        response = client.delete(f"/admin/users/{managed['id']}", headers=headers)

        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()

