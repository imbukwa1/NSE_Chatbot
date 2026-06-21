from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from knowledge.models import QueryLog
from knowledge.services.llm import FallbackAnswer, generate_nse_fallback


class LlmFallbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_knowledge_base", verbosity=0)

    def setUp(self):
        self.client = APIClient()

    def test_confident_kb_answer_does_not_use_fallback(self):
        response = self.client.get("/api/kb/search", {"q": "What is a dividend?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["strategy"], "keyword")
        self.assertFalse(QueryLog.objects.latest("created_at").used_fallback)

    @patch("knowledge.views.generate_nse_fallback")
    def test_low_confidence_nse_query_uses_and_logs_fallback(self, fallback):
        fallback.return_value = FallbackAnswer("A beginner-friendly NSE answer.", "featherless")
        response = self.client.get("/api/kb/search", {"q": "How do NSE shareholders earn money?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["strategy"], "featherless")
        self.assertTrue(QueryLog.objects.latest("created_at").used_fallback)

    def test_out_of_scope_question_is_blocked(self):
        response = self.client.get("/api/kb/search", {"q": "How do I bake sourdough bread?"})
        self.assertEqual(response.data["strategy"], "guardrail")
        self.assertIn("Nairobi Securities Exchange", response.data["answer"])

    @patch.dict("os.environ", {"FEATHERLESS_API_KEY": "", "FEATHERLESS_CHAT_MODEL": ""})
    def test_missing_provider_configuration_is_safe(self):
        result = generate_nse_fallback("Explain an NSE rights issue")
        self.assertEqual(result.source, "local_fallback")
