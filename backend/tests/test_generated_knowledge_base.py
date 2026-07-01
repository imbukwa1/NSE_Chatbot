import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

import main
from services.knowledge_base_generator import generate_entries
from services.knowledge_base_service import answer_knowledge_question


class GeneratedKnowledgeBaseTests(unittest.TestCase):
    def test_generator_creates_200_beginner_entries(self):
        entries = generate_entries()

        self.assertEqual(len(entries), 200)
        self.assertEqual(
            {entry["difficulty"] for entry in entries},
            {"beginner"},
        )
        self.assertIn("category", entries[0])
        self.assertIn("question", entries[0])
        self.assertIn("answer", entries[0])

    def test_knowledge_base_answers_common_beginner_question(self):
        response = answer_knowledge_question("What are dividends?")

        self.assertIsNotNone(response)
        self.assertEqual(response["type"], "educational")
        self.assertEqual(response["data"]["source"], "Knowledge Base")
        self.assertIn("shareholders", response["message"])

    def test_chat_uses_generated_knowledge_base_for_learning(self):
        client = TestClient(main.app)
        response = client.post("/chat", json={"query": "What are dividends?"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["type"], "educational")
        self.assertEqual(body["data"]["source"], "Knowledge Base")
        self.assertNotIn("Please mention a specific stock", body["message"])


if __name__ == "__main__":
    unittest.main()
