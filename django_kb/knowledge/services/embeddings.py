import math

from django.conf import settings

from knowledge.models import KnowledgeBase, KnowledgeEmbedding
from knowledge.services.search import SearchMatch


def get_encoder():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Embeddings require sentence-transformers. Install django_kb/requirements-embeddings.txt."
        ) from exc
    return SentenceTransformer(settings.KB_EMBEDDING_MODEL)


def entry_document(entry):
    tags = ", ".join(entry.tags or [])
    return f"Question: {entry.question}\nAnswer: {entry.answer}\nKeywords: {entry.keywords}\nTags: {tags}"


def rebuild_embeddings(encoder=None):
    encoder = encoder or get_encoder()
    entries = list(KnowledgeBase.objects.filter(is_active=True).order_by("id"))
    if not entries:
        return 0
    vectors = encoder.encode([entry_document(entry) for entry in entries], normalize_embeddings=True)
    model_name = settings.KB_EMBEDDING_MODEL
    for entry, raw_vector in zip(entries, vectors):
        vector = [float(value) for value in raw_vector]
        KnowledgeEmbedding.objects.update_or_create(
            entry=entry,
            defaults={"vector": vector, "dimensions": len(vector), "model_name": model_name},
        )
    KnowledgeEmbedding.objects.exclude(entry__in=entries).delete()
    return len(entries)


def cosine_similarity(left, right):
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def semantic_search(query, category=None, tag=None, encoder=None):
    encoder = encoder or get_encoder()
    raw_query_vector = encoder.encode([query], normalize_embeddings=True)[0]
    query_vector = [float(value) for value in raw_query_vector]
    queryset = KnowledgeEmbedding.objects.select_related("entry", "entry__category").filter(entry__is_active=True)
    if category:
        queryset = queryset.filter(entry__category__slug__iexact=category) | queryset.filter(entry__category__name__iexact=category)
    candidates = list(queryset[:5000])
    if tag:
        wanted = tag.strip().lower()
        candidates = [item for item in candidates if wanted in {value.lower() for value in item.entry.tags or []}]
    if not candidates:
        return None
    confidence, embedding = max(
        ((cosine_similarity(query_vector, item.vector), item) for item in candidates),
        key=lambda item: item[0],
    )
    return SearchMatch(entry=embedding.entry, confidence=round(max(0.0, confidence), 4), strategy="semantic")
