import sys
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

from auth.jwt_handler import decode_access_token
from main import app


client = TestClient(app)


def unique_email() -> str:
    return f"auth-test-{uuid4().hex[:12]}@example.com"


def register_payload(email: str | None = None) -> dict:
    return {
        "full_name": "Auth Test User",
        "email": email or unique_email(),
        "password": "StrongPass123",
    }


class AuthTests(unittest.TestCase):
    def test_register_user_success(self):
        response = client.post("/auth/register", json=register_payload())

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["message"], "User registered successfully")
        self.assertTrue(body["data"]["user"]["email"].endswith("@example.com"))
        self.assertNotIn("hashed_password", body["data"]["user"])

    def test_duplicate_email_prevention(self):
        payload = register_payload()
        first = client.post("/auth/register", json=payload)
        duplicate = client.post("/auth/register", json=payload)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(
            duplicate.json()["detail"],
            "An account with this email already exists.",
        )

    def test_login_success_and_token_verification(self):
        payload = register_payload()
        client.post("/auth/register", json=payload)

        response = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        token = body["data"]["access_token"]
        decoded = decode_access_token(token)
        self.assertEqual(decoded["sub"], payload["email"].lower())
        self.assertEqual(decoded["role"], "user")

    def test_invalid_login_fails(self):
        payload = register_payload()
        client.post("/auth/register", json=payload)

        response = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid email or password.")

    def test_protected_route_requires_token(self):
        response = client.get("/auth/me")

        self.assertEqual(response.status_code, 401)

    def test_protected_route_accepts_valid_token(self):
        payload = register_payload()
        client.post("/auth/register", json=payload)
        login = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        token = login.json()["data"]["access_token"]

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["user"]["email"], payload["email"].lower())

    def test_admin_route_rejects_regular_user(self):
        payload = register_payload()
        client.post("/auth/register", json=payload)
        login = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        token = login.json()["data"]["access_token"]

        response = client.get(
            "/auth/admin/check",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Admin access is required.")


if __name__ == "__main__":
    unittest.main()
