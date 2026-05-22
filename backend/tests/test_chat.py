import sys
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

from main import app


client = TestClient(app)


def make_user() -> tuple[dict, str]:
    payload = {
        "full_name": "Chat Test User",
        "email": f"chat-test-{uuid4().hex[:12]}@example.com",
        "password": "StrongPass123",
    }
    client.post("/auth/register", json=payload)
    login = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return payload, login.json()["data"]["access_token"]


class ChatHistoryTests(unittest.TestCase):
    def test_create_and_list_sessions(self):
        _, token = make_user()
        headers = {"Authorization": f"Bearer {token}"}

        created = client.post(
            "/chat/sessions",
            json={"title": "Safaricom analysis"},
            headers=headers,
        )
        listed = client.get("/chat/sessions", headers=headers)

        self.assertEqual(created.status_code, 201)
        self.assertEqual(listed.status_code, 200)
        self.assertGreaterEqual(len(listed.json()["data"]["sessions"]), 1)

    def test_add_message_saves_user_and_ai_messages(self):
        _, token = make_user()
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post("/chat/sessions", json={}, headers=headers)
        session_id = created.json()["data"]["session"]["id"]

        response = client.post(
            f"/chat/sessions/{session_id}/messages",
            json={"message_text": "Safaricom share price"},
            headers=headers,
        )
        retrieved = client.get(f"/chat/sessions/{session_id}", headers=headers)

        self.assertEqual(response.status_code, 200)
        body = response.json()["data"]
        self.assertEqual(body["user_message"]["sender_type"], "user")
        self.assertEqual(body["ai_message"]["sender_type"], "ai")
        self.assertTrue(body["ai_message"]["message_text"])
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(len(retrieved.json()["data"]["session"]["messages"]), 2)

    def test_user_cannot_access_other_users_session(self):
        _, token_one = make_user()
        _, token_two = make_user()
        session = client.post(
            "/chat/sessions",
            json={"title": "Private"},
            headers={"Authorization": f"Bearer {token_one}"},
        )
        session_id = session.json()["data"]["session"]["id"]

        response = client.get(
            f"/chat/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token_two}"},
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_session_removes_history(self):
        _, token = make_user()
        headers = {"Authorization": f"Bearer {token}"}
        session = client.post("/chat/sessions", json={}, headers=headers)
        session_id = session.json()["data"]["session"]["id"]

        deleted = client.delete(f"/chat/sessions/{session_id}", headers=headers)
        retrieved = client.get(f"/chat/sessions/{session_id}", headers=headers)

        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(retrieved.status_code, 404)

    def test_chat_routes_require_authentication(self):
        response = client.get("/chat/sessions")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

