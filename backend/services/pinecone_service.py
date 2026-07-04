import os
from typing import Iterable, Optional

from dotenv import load_dotenv

from services.llm_service import get_openai_client

load_dotenv()

try:
    from pinecone import Pinecone, ServerlessSpec
except Exception:  # pragma: no cover - depends on local installation state
    Pinecone = None
    ServerlessSpec = None


DEFAULT_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "nse-advisor")
DEFAULT_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "annual-reports")
DEFAULT_KB_NAMESPACE = os.getenv("PINECONE_KB_NAMESPACE", "knowledge_base")
DEFAULT_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"
)
DEFAULT_DIMENSION = int(os.getenv("PINECONE_DIMENSION", "1536"))
DEFAULT_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
DEFAULT_REGION = os.getenv("PINECONE_REGION", "us-east-1")

_pinecone_client: Optional["Pinecone"] = None
_index = None


def _embed_texts(texts: Iterable[str]) -> list[list[float]]:
    client = get_openai_client()
    clean_texts = [text.strip() for text in texts if text and text.strip()]
    if not clean_texts:
        return []

    response = client.embeddings.create(
        model=DEFAULT_EMBEDDING_MODEL,
        input=clean_texts,
    )
    return [item.embedding for item in response.data]


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """Public embedding helper for batch-oriented RAG services."""
    return _embed_texts(texts)


def get_pinecone_client() -> "Pinecone":
    global _pinecone_client

    if Pinecone is None:
        raise RuntimeError(
            "Pinecone SDK is unavailable. Install `pinecone` instead of `pinecone-client`."
        )

    if _pinecone_client is None:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "PINECONE_API_KEY is missing. Add it to your environment or .env file."
            )
        _pinecone_client = Pinecone(api_key=api_key)

    return _pinecone_client


def get_index(index_name: str = DEFAULT_INDEX_NAME):
    global _index

    if _index is not None:
        return _index

    client = get_pinecone_client()
    existing_indexes = client.list_indexes().names()

    if index_name not in existing_indexes:
        client.create_index(
            name=index_name,
            dimension=DEFAULT_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud=DEFAULT_CLOUD, region=DEFAULT_REGION),
        )

    _index = client.Index(index_name)
    return _index


def upsert_documents(
    text_chunks: list[str] | list[dict],
    namespace: str = DEFAULT_NAMESPACE,
    index_name: str = DEFAULT_INDEX_NAME,
) -> dict:
    if not text_chunks:
        return {"upserted_count": 0, "namespace": namespace}

    normalized_records = []
    for position, chunk in enumerate(text_chunks):
        if isinstance(chunk, str):
            text = chunk.strip()
            metadata = {"text": text}
            record_id = f"doc-{position}"
        else:
            text = str(chunk.get("text", "")).strip()
            metadata = {key: value for key, value in chunk.items() if key != "id"}
            metadata["text"] = text
            record_id = chunk.get("id") or f"doc-{position}"

        if text:
            normalized_records.append(
                {"id": record_id, "text": text, "metadata": metadata}
            )

    embeddings = _embed_texts(record["text"] for record in normalized_records)
    vectors = [
        {
            "id": record["id"],
            "values": embedding,
            "metadata": record["metadata"],
        }
        for record, embedding in zip(normalized_records, embeddings)
    ]

    if not vectors:
        return {"upserted_count": 0, "namespace": namespace}

    index = get_index(index_name)
    index.upsert(vectors=vectors, namespace=namespace)

    return {"upserted_count": len(vectors), "namespace": namespace}


def upsert_vectors(
    vectors: list[dict],
    namespace: str = DEFAULT_NAMESPACE,
    index_name: str = DEFAULT_INDEX_NAME,
) -> dict:
    """Upsert pre-embedded vectors into Pinecone."""
    clean_vectors = [
        vector
        for vector in vectors
        if vector.get("id") and vector.get("values") and vector.get("metadata") is not None
    ]
    if not clean_vectors:
        return {"upserted_count": 0, "namespace": namespace}

    index = get_index(index_name)
    index.upsert(vectors=clean_vectors, namespace=namespace)
    return {"upserted_count": len(clean_vectors), "namespace": namespace}


def query_documents(
    query: str,
    namespace: str = DEFAULT_NAMESPACE,
    index_name: str = DEFAULT_INDEX_NAME,
    top_k: int = 4,
) -> list[dict]:
    if not query.strip():
        return []

    query_embeddings = _embed_texts([query])
    if not query_embeddings:
        return []

    index = get_index(index_name)
    response = index.query(
        namespace=namespace,
        vector=query_embeddings[0],
        top_k=top_k,
        include_metadata=True,
    )

    matches = []
    for match in getattr(response, "matches", []) or []:
        metadata = getattr(match, "metadata", {}) or {}
        matches.append(
            {
                "id": getattr(match, "id", None),
                "score": getattr(match, "score", 0.0),
                "text": metadata.get("text", ""),
                "ticker": metadata.get("ticker"),
                "source": metadata.get("source"),
            }
        )

    return matches


def get_namespace_counts(
    index_name: str = DEFAULT_INDEX_NAME,
    namespaces: list[str] | tuple[str, ...] | None = None,
) -> dict[str, int]:
    index = get_index(index_name)
    stats = index.describe_index_stats()
    namespace_stats = getattr(stats, "namespaces", {}) or {}
    target_namespaces = namespaces or namespace_stats.keys()

    counts = {}
    for namespace in target_namespaces:
        details = namespace_stats.get(namespace)
        counts[namespace] = int(getattr(details, "vector_count", 0) or 0)
    return counts
