import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

import main
import intent_router
from services import llm_service


class FeatherlessProviderTests(unittest.TestCase):
    def tearDown(self):
        llm_service.reset_clients_for_tests()
        intent_router._client = None

    def test_featherless_client_initializes_from_env(self):
        with patch.dict(
            os.environ,
            {
                "FEATHERLESS_API_KEY": "test-featherless-key",
                "FEATHERLESS_BASE_URL": "https://api.featherless.ai/v1",
                "FEATHERLESS_CHAT_MODEL": "test-chat-model",
            },
            clear=False,
        ):
            llm_service.reset_clients_for_tests()
            settings = llm_service.get_provider_settings()
            client = llm_service.get_chat_client()

        self.assertEqual(settings["provider"], "featherless")
        self.assertEqual(settings["model"], "test-chat-model")
        self.assertTrue(str(client.base_url).startswith("https://api.featherless.ai/v1"))

    def test_missing_featherless_key_is_safe(self):
        with patch.dict(
            os.environ,
            {
                "FEATHERLESS_API_KEY": "",
                "FEATHERLESS_CHAT_MODEL": "test-chat-model",
            },
            clear=False,
        ):
            llm_service.reset_clients_for_tests()
            self.assertFalse(llm_service.has_chat_provider())
            with self.assertRaises(RuntimeError):
                llm_service.get_chat_client()

    def test_intent_classification_falls_back_when_provider_fails(self):
        class FailingCompletions:
            def create(self, **kwargs):
                raise RuntimeError("invalid Featherless model")

        class FailingChat:
            completions = FailingCompletions()

        class FailingClient:
            chat = FailingChat()

        llm_service._chat_client = FailingClient()
        with patch.dict(
            os.environ,
            {
                "FEATHERLESS_API_KEY": "test-featherless-key",
                "FEATHERLESS_CHAT_MODEL": "bad-model",
            },
            clear=False,
        ):
            result = llm_service.classify_query("Compare KCB and Equity")

        self.assertEqual(result["type"], "compare")

    def test_chat_endpoint_works_without_featherless_provider(self):
        client = TestClient(main.app)
        with patch.object(main, "_has_ai_provider", return_value=False):
            response = client.post("/chat", json={"query": "Safaricom share price"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("message", body)
        self.assertIn("disclaimer", body)

    def test_existing_openai_sdk_import_still_available(self):
        self.assertIsNotNone(llm_service.OpenAI)


if __name__ == "__main__":
    unittest.main()
