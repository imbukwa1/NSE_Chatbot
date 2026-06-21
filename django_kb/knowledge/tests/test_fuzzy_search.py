from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient


class FuzzySearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_knowledge_base", verbosity=0)

    def setUp(self):
        self.client = APIClient()

    def test_typo_matches_dividend_question(self):
        response = self.client.get("/api/kb/search", {"q": "what is a dividence"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["question"], "What is a dividend?")
        self.assertGreater(response.data["confidence"], 0.75)

    def test_paraphrased_market_question_is_retrieved(self):
        response = self.client.get("/api/kb/search", {"q": "please explain a bear market"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("bear market", response.data["question"].lower())

    def test_unrelated_query_has_low_confidence(self):
        response = self.client.get("/api/kb/search", {"q": "how do I bake sourdough bread"})
        self.assertEqual(response.status_code, 200)
        self.assertLess(response.data["confidence"], 0.75)
