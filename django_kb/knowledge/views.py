from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import KnowledgeSearchResultSerializer
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
    if match is None:
        return Response({"question": "", "answer": "", "confidence": 0.0, "strategy": "keyword"})

    payload = KnowledgeSearchResultSerializer(match.entry).data
    payload.update({"confidence": match.confidence, "strategy": match.strategy})
    return Response(payload)
