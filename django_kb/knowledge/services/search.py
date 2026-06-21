import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from django.db.models import Q

from knowledge.models import KnowledgeBase

try:
    from rapidfuzz import fuzz
except ImportError:  # The service remains usable before optional dependencies are installed.
    fuzz = None


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize(value):
    return " ".join(TOKEN_PATTERN.findall((value or "").lower()))


def tokens(value):
    return set(normalize(value).split())


@dataclass(frozen=True)
class SearchMatch:
    entry: KnowledgeBase
    confidence: float
    strategy: str


def keyword_score(query, entry):
    normalized_query = normalize(query)
    query_tokens = tokens(query)
    if not query_tokens:
        return 0.0

    question = normalize(entry.question)
    keyword_text = normalize(entry.keywords)
    tag_text = normalize(" ".join(entry.tags or []))
    answer = normalize(entry.answer)

    score = 0.0
    if normalized_query == question:
        return 1.0
    if normalized_query in question:
        score += 0.55
    score += 0.30 * len(query_tokens & tokens(question)) / len(query_tokens)
    score += 0.10 * len(query_tokens & tokens(keyword_text)) / len(query_tokens)
    score += 0.05 * len(query_tokens & tokens(tag_text)) / len(query_tokens)
    score += 0.02 * len(query_tokens & tokens(answer)) / len(query_tokens)
    return min(round(score, 4), 0.99)


def keyword_search(query, category=None, tag=None):
    normalized_query = normalize(query)
    if not normalized_query:
        return None

    queryset = KnowledgeBase.objects.filter(is_active=True).select_related("category")
    if category:
        queryset = queryset.filter(Q(category__slug__iexact=category) | Q(category__name__iexact=category))

    terms = list(tokens(normalized_query))
    text_filter = Q()
    for term in terms:
        text_filter |= Q(question__icontains=term) | Q(answer__icontains=term) | Q(keywords__icontains=term)
    candidates = list(queryset.filter(text_filter)[:500]) if text_filter else []
    if tag:
        wanted_tag = normalize(tag)
        candidates = [entry for entry in candidates if wanted_tag in {normalize(value) for value in entry.tags or []}]

    ranked = [(keyword_score(query, entry), entry) for entry in candidates]
    ranked = [item for item in ranked if item[0] > 0]
    if not ranked:
        return None
    confidence, entry = max(ranked, key=lambda item: item[0])
    return SearchMatch(entry=entry, confidence=confidence, strategy="keyword")


def _similarity(left, right):
    if not left or not right:
        return 0.0
    if fuzz is not None:
        return fuzz.WRatio(left, right) / 100.0
    return SequenceMatcher(None, left, right).ratio()


def fuzzy_score(query, entry):
    normalized_query = normalize(query)
    values = [
        normalize(entry.question),
        normalize(entry.keywords),
        *(normalize(tag) for tag in entry.tags or []),
        *(normalize(synonym.phrase) for synonym in entry.synonyms.all()),
    ]
    return round(max((_similarity(normalized_query, value) for value in values), default=0.0), 4)


def fuzzy_search(query, category=None, tag=None):
    normalized_query = normalize(query)
    if not normalized_query:
        return None
    queryset = KnowledgeBase.objects.filter(is_active=True).select_related("category").prefetch_related("synonyms")
    if category:
        queryset = queryset.filter(Q(category__slug__iexact=category) | Q(category__name__iexact=category))
    candidates = list(queryset[:2000])
    if tag:
        wanted_tag = normalize(tag)
        candidates = [entry for entry in candidates if wanted_tag in {normalize(value) for value in entry.tags or []}]
    ranked = [(fuzzy_score(query, entry), entry) for entry in candidates]
    if not ranked:
        return None
    confidence, entry = max(ranked, key=lambda item: item[0])
    return SearchMatch(entry=entry, confidence=confidence, strategy="fuzzy")


def retrieve_best(query, category=None, tag=None):
    matches = [
        keyword_search(query, category=category, tag=tag),
        fuzzy_search(query, category=category, tag=tag),
    ]
    matches = [match for match in matches if match is not None]
    return max(matches, key=lambda match: match.confidence) if matches else None
