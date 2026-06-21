from django.test import TestCase, override_settings

from knowledge.models import KnowledgeBase, KnowledgeCategory, KnowledgeEmbedding
from knowledge.services.embeddings import cosine_similarity, rebuild_embeddings, semantic_search


class FakeEncoder:
    def encode(self, documents, normalize_embeddings=True):
        vectors = []
        for document in documents:
            text = document.lower()
            vectors.append([1.0, 0.0] if "dividend" in text or "shareholders earn" in text else [0.0, 1.0])
        return vectors


@override_settings(KB_EMBEDDING_MODEL="test-encoder")
class EmbeddingSearchTests(TestCase):
    def setUp(self):
        category = KnowledgeCategory.objects.create(name="Basic Concepts", slug="basic-concepts")
        self.dividend = KnowledgeBase.objects.create(
            category=category,
            question="What is a dividend?",
            answer="A dividend is profit distributed to shareholders.",
        )
        KnowledgeBase.objects.create(
            category=category,
            question="What is a market order?",
            answer="A market order trades at the current available price.",
        )

    def test_cosine_similarity(self):
        self.assertEqual(cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertEqual(cosine_similarity([1, 0], [0, 1]), 0.0)

    def test_rebuild_and_semantic_query(self):
        self.assertEqual(rebuild_embeddings(encoder=FakeEncoder()), 2)
        self.assertEqual(KnowledgeEmbedding.objects.count(), 2)
        match = semantic_search("How do shareholders earn money?", encoder=FakeEncoder())
        self.assertEqual(match.entry, self.dividend)
        self.assertEqual(match.strategy, "semantic")
        self.assertEqual(match.confidence, 1.0)
