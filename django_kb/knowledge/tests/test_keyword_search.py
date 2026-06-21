from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient


class KeywordSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_knowledge_base", verbosity=0)

    def setUp(self):
        self.client = APIClient()

    def test_exact_question_returns_best_entry(self):
        response = self.client.get("/api/kb/search", {"q": "What is a dividend?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["question"], "What is a dividend?")
        self.assertEqual(response.data["confidence"], 1.0)

    def test_category_and_tag_filters_are_supported(self):
        response = self.client.get(
            "/api/kb/search",
            {"q": "inflation", "category": "investment-basics", "tag": "investment_basics"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "Investment Basics")

    def test_missing_query_is_rejected(self):
        response = self.client.get("/api/kb/search")
        self.assertEqual(response.status_code, 400)
