from django.core.management import call_command
from django.test import TestCase

from knowledge.models import KnowledgeBase, KnowledgeCategory


class KnowledgeBaseStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_knowledge_base", verbosity=0)

    def test_seed_contains_expected_volume_and_categories(self):
        self.assertEqual(KnowledgeBase.objects.count(), 200)
        self.assertEqual(KnowledgeCategory.objects.count(), 4)

    def test_seed_is_idempotent(self):
        call_command("seed_knowledge_base", verbosity=0)
        self.assertEqual(KnowledgeBase.objects.count(), 200)

    def test_entries_are_admin_editable_and_search_ready(self):
        dividend = KnowledgeBase.objects.get(question="What is a dividend?")
        self.assertEqual(dividend.difficulty, KnowledgeBase.Difficulty.BEGINNER)
        self.assertTrue(dividend.tags)
        self.assertTrue(dividend.keywords)
