from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from .models import QueryLog
from .serializers import KnowledgeSearchResultSerializer
from .services.llm import generate_nse_fallback
from .services.search import retrieve_best


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "service": "nse-knowledge-base"})


@api_view(["GET"])
def search(request):
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response({"detail": "The q query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

    match = retrieve_best(
        query,
        category=request.query_params.get("category"),
        tag=request.query_params.get("tag"),
    )
    if match is None or match.confidence < settings.KB_MIN_CONFIDENCE:
        fallback = generate_nse_fallback(query)
        QueryLog.objects.create(
            query=query,
            matched_entry=match.entry if match else None,
            strategy=fallback.source,
            confidence=match.confidence if match else 0.0,
            used_fallback=True,
        )
        return Response({
            "question": query,
            "answer": fallback.answer,
            "confidence": match.confidence if match else 0.0,
            "strategy": fallback.source,
            "disclaimer": "This is educational information, not financial advice.",
        })

    payload = KnowledgeSearchResultSerializer(match.entry).data
    payload.update({"confidence": match.confidence, "strategy": match.strategy})
    QueryLog.objects.create(
        query=query,
        matched_entry=match.entry,
        strategy=match.strategy,
        confidence=match.confidence,
        used_fallback=False,
    )
    return Response(payload)
