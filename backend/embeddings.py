"""
Pinecone Vector Embeddings for NSE Stocks
Handles embedding generation and Pinecone vector search for stock fuzzy matching
"""

import logging
import os
from typing import Any

from openai import OpenAI
from pinecone import Pinecone

import database

logger = logging.getLogger(__name__)

# Initialize clients
_openai_client = None
_pinecone_client = None

STOCKS_INDEX_NAME = os.getenv("PINECONE_STOCKS_INDEX", "nse-stocks")
STOCKS_NAMESPACE = os.getenv("PINECONE_STOCKS_NAMESPACE", "stocks")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSION = 1536  # text-embedding-3-small dimension


def _get_openai_client():
    """Get or initialize OpenAI client."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. Embeddings will be unavailable.")
            return None
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _get_pinecone_client():
    """Get or initialize Pinecone client."""
    global _pinecone_client
    if _pinecone_client is None:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            logger.warning("PINECONE_API_KEY not set. Vector search will be unavailable.")
            return None
        _pinecone_client = Pinecone(api_key=api_key)
    return _pinecone_client


def _get_index():
    """Get Pinecone index for stocks."""
    client = _get_pinecone_client()
    if not client:
        return None
    try:
        return client.Index(STOCKS_INDEX_NAME)
    except Exception as e:
        logger.error(f"Failed to get Pinecone index '{STOCKS_INDEX_NAME}': {e}")
        return None


def get_embedding(text: str) -> list[float] | None:
    """
    Generate embedding for text using OpenAI.

    Args:
        text: Text to embed

    Returns:
        Embedding vector, or None if error
    """
    client = _get_openai_client()
    if not client:
        logger.warning("OpenAI client not available for embeddings")
        return None

    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None


def build_stock_text_blob(stock: dict[str, Any]) -> str:
    """
    Build a text blob for a stock with all relevant information.

    Used for embedding and vector search.

    Args:
        stock: Stock dict with ticker, name, price, change_pct, pe_ratio, dividend_yield

    Returns:
        Formatted text blob

    Example:
        "Equity Bank (EQTY) — banking sector, KES 52.50, +1.2% today, PE 6.2, Yield 4.1%"
    """
    ticker = stock.get("ticker", "UNKNOWN").upper()
    name = stock.get("name", "Unknown Company")
    price = stock.get("price", 0)
    change_pct = stock.get("change_pct", 0)
    pe_ratio = stock.get("pe_ratio", 0)
    dividend_yield = stock.get("dividend_yield", 0)
    volume = stock.get("volume", 0)

    # Determine sector from name hints
    name_lower = name.lower()
    sector = "general"
    if any(term in name_lower for term in ["bank", "equity", "kcb", "stanbic"]):
        sector = "banking"
    elif any(term in name_lower for term in ["power", "energy", "kem"]):
        sector = "energy"
    elif any(term in name_lower for term in ["brew", "bab", "eabl"]):
        sector = "beverages"
    elif any(term in name_lower for term in ["airways", "kq"]):
        sector = "aviation"
    elif any(term in name_lower for term in ["tobacco", "bat"]):
        sector = "tobacco"
    elif any(term in name_lower for term in ["insur", "brit", "cic"]):
        sector = "insurance"

    # Build comprehensive text blob
    blob = (
        f"{name} ({ticker}) — {sector} sector, "
        f"KES {price:,.2f}, "
        f"{'+' if change_pct >= 0 else ''}{change_pct:.1f}% today"
    )

    if pe_ratio > 0:
        blob += f", PE ratio {pe_ratio:.1f}"
    if dividend_yield > 0:
        blob += f", Dividend yield {dividend_yield:.1f}%"
    if volume > 0:
        blob += f", Volume {volume:,.0f}"

    return blob


async def upsert_stock_vectors(
    stocks: list[dict[str, Any]] | None = None, batch_size: int = 100
) -> int:
    """
    Embed all stocks and upsert vectors to Pinecone.

    Args:
        stocks: List of stock dictionaries to embed. If None, fetches from database.

    Returns:
        Number of stocks successfully upserted
    """
    client = _get_openai_client()
    index = _get_index()
    if not index or not client:
        logger.warning("OpenAI or Pinecone is not available. Skipping vector upsert.")
        return 0

    # Get stocks from database if not provided

    if stocks is None:
        stocks = database.get_all_stocks()


    if not stocks:
        logger.warning("No stocks available for embedding")
        return 0


    try:
        tickers = []
        blobs = []
        stock_map = {}

        for stock in stocks:
            ticker = stock.get("ticker", "").upper()
            if not ticker:
                continue
            blobs.append(build_stock_text_blob(stock))
            tickers.append(ticker)
            stock_map[ticker] = stock

        if not blobs:
            logger.warning("No stock text prepared for embedding")
            return 0

        logger.info(f"Generating embeddings for {len(blobs)} stocks in one batch...")
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=blobs)

        vectors_to_upsert = []
        for i, ticker in enumerate(tickers):
            stock = stock_map[ticker]
            vectors_to_upsert.append({
                "id": ticker,
                "values": response.data[i].embedding,
                "metadata": {
                    "name": stock.get("name", ""),
                    "price": float(stock.get("price", 0)),
                    "change_pct": float(stock.get("change_pct", 0)),
                    "pe_ratio": float(stock.get("pe_ratio", 0)),
                    "dividend_yield": float(stock.get("dividend_yield", 0)),
                    "ticker": ticker,
                    "text_blob": blobs[i],
                }
            })

        if not vectors_to_upsert:
            logger.warning("No vectors prepared for upsert")
            return 0

        total_upserted = 0

        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i : i + batch_size]
            try:
                upsert_response = index.upsert(
                    vectors=batch,
                    namespace=STOCKS_NAMESPACE,
                    show_progress=False,
                )
                batch_count = len(batch)
                total_upserted += batch_count
                logger.info(f"Upserted {batch_count} stock vectors (batch {i // batch_size + 1})")
            except Exception as e:
                logger.error(f"Error upserting batch {i // batch_size + 1}: {e}")
                continue

        logger.info(f"Successfully upserted {total_upserted}/{len(stocks)} stock vectors to Pinecone")
        return total_upserted

    except Exception as e:
        logger.error(f"Error upserting stock vectors: {e}")
        return 0


async def query_stock_by_description(
    query: str,
    top_k: int = 5,
    threshold: float = 0.6
) -> list[dict[str, Any]]:
    """
    Query Pinecone to find stocks matching a description.

    Used for fuzzy entity matching (e.g., "that big bank" → matches EQTY, KCB, SCBK).

    Args:
        query: User's description (e.g., "top performing bank")
        top_k: Number of results to return
        threshold: Minimum similarity score (0-1)

    Returns:
        List of matching stocks with similarity scores, sorted by score descending

    Example:
        >>> matches = await query_stock_by_description("big bank with dividends")
        >>> # Returns EQTY, KCB, SCBK with scores
    """
    index = _get_index()
    if not index:
        logger.warning("Pinecone index not available for query")
        return []

    # Get embedding for query
    query_embedding = get_embedding(query)
    if not query_embedding:
        logger.error("Failed to generate query embedding")
        return []

    try:
        # Query Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=STOCKS_NAMESPACE,
        )

        matches = []
        for match in results.get("matches", []):
            score = float(match.get("score", 0))

            # Filter by threshold
            if score < threshold:
                logger.debug(f"Skipping match {match['id']} with score {score:.3f} (below threshold)")
                continue

            metadata = match.get("metadata", {})
            matches.append({
                "ticker": match["id"],
                "name": metadata.get("name", ""),
                "price": metadata.get("price", 0),
                "change_pct": metadata.get("change_pct", 0),
                "similarity_score": score,
                "confidence": score,  # Alias for intent router compatibility
            })

        logger.info(f"Vector search for '{query}' returned {len(matches)} matches above threshold {threshold}")
        return matches

    except Exception as e:
        logger.error(f"Error querying Pinecone: {e}")
        return []


def get_stock_info_by_vector(ticker: str) -> dict[str, Any] | None:
    """
    Retrieve stock info from vector metadata by ticker ID.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Stock info dict, or None if not found
    """
    index = _get_index()
    if not index:
        return None

    try:
        # Fetch vector by ID
        results = index.fetch(ids=[ticker], namespace=STOCKS_NAMESPACE)

        if not results.get("vectors"):
            logger.warning(f"Stock {ticker} not found in Pinecone")
            return None

        vector_data = results["vectors"].get(ticker, {})
        metadata = vector_data.get("metadata", {})

        return {
            "ticker": ticker,
            "name": metadata.get("name", ""),
            "price": metadata.get("price", 0),
            "change_pct": metadata.get("change_pct", 0),
            "pe_ratio": metadata.get("pe_ratio", 0),
            "dividend_yield": metadata.get("dividend_yield", 0),
            "text_blob": metadata.get("text_blob", ""),
        }

    except Exception as e:
        logger.error(f"Error fetching stock info for {ticker}: {e}")
        return None


def delete_stock_vectors(tickers: list[str] | None = None) -> int:
    """
    Delete stock vectors from Pinecone.

    Args:
        tickers: List of ticker symbols to delete. If None, deletes all.

    Returns:
        Number of vectors deleted
    """
    index = _get_index()
    if not index:
        logger.warning("Pinecone index not available for deletion")
        return 0

    try:
        if tickers:
            # Delete specific vectors
            delete_response = index.delete(
                ids=tickers,
                namespace=STOCKS_NAMESPACE,
            )
            count = len(tickers)
            logger.info(f"Deleted {count} stock vectors")
            return count
        else:
            # Delete all vectors in namespace (delete and recreate)
            logger.warning("Deleting all stock vectors from namespace")
            # Note: Pinecone doesn't have bulk delete by namespace
            # Would need to iterate or use delete_by_filter in advanced usage
            return 0

            # Correct way to delete everything in a namespace
            logger.warning(f"Deleting all vectors in namespace: {STOCKS_NAMESPACE}")
            index.delete(delete_all=True, namespace=STOCKS_NAMESPACE)
            return 1 # Returns 1 to indicate success

    except Exception as e:
        logger.error(f"Error deleting stock vectors: {e}")
        return 0


if __name__ == "__main__":
    # Quick test
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        # Test building text blob
        sample_stock = {
            "ticker": "SCOM",
            "name": "Safaricom PLC",
            "price": 33.50,
            "change_pct": 2.3,
            "pe_ratio": 15.2,
            "dividend_yield": 3.5,
            "volume": 1000000,
        }

        blob = build_stock_text_blob(sample_stock)
        print(f"Text blob: {blob}")

        # Test embedding
        embedding = get_embedding("major telecommunications company Kenya")
        if embedding:
            print(f"✓ Embedding generated ({len(embedding)} dimensions)")
        else:
            print("✗ Failed to generate embedding (check OPENAI_API_KEY)")

        # Test upsert
        stocks = database.get_all_stocks()
        if stocks:
            count = await upsert_stock_vectors(stocks[:5])  # Test with first 5
            print(f"✓ Upserted {count} vectors")
        else:
            print("No stocks in database")

        # Test query
        results = await query_stock_by_description("big bank with dividends")
        if results:
            print(f"✓ Vector search found {len(results)} matches")
            for r in results:
                print(f"  - {r['ticker']}: {r['name']} (score: {r['similarity_score']:.3f})")
        else:
            print("✗ No matches found (Pinecone may not be configured)")

    asyncio.run(test())
