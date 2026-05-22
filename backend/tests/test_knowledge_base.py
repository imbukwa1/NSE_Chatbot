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
    email = f"kb-admin-{uuid4().hex[:12]}@example.com"
    with database.SessionLocal() as db:
        create_user(
            db,
            full_name="KB Admin",
            email=email,
            password="StrongPass123",
            role="admin",
        )
    login = client.post("/auth/login", json={"email": email, "password": "StrongPass123"})
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


class KnowledgeBaseTests(unittest.TestCase):
    def test_knowledge_base_crud(self):
        headers = admin_headers()
        created = client.post(
            "/admin/knowledge-base",
            json={
                "category": "dividends",
                "question": "What are dividends?",
                "answer": "Dividends are payments made to shareholders.",
                "source": "admin",
            },
            headers=headers,
        )
        entry_id = created.json()["data"]["entry"]["id"]
        listed = client.get("/admin/knowledge-base", headers=headers)
        updated = client.put(
            f"/admin/knowledge-base/{entry_id}",
            json={"answer": "Updated dividend explanation."},
            headers=headers,
        )
        deleted = client.delete(f"/admin/knowledge-base/{entry_id}", headers=headers)

        self.assertEqual(created.status_code, 201)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["entry"]["answer"], "Updated dividend explanation.")
        self.assertEqual(deleted.status_code, 200)

    def test_knowledge_base_requires_admin(self):
        response = client.get("/admin/knowledge-base")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

