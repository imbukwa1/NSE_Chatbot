import asyncio
import json
import os
import re
import time
from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from services.advisor_logic import extract_tickers
from services import llm_service, pinecone_service
from services.llm_service import classify_query, generate_stream_response
from services.pinecone_service import get_namespace_counts, query_documents
from services.structured_data import get_stock_data, load_stock_data

app = FastAPI()

# ── CORS ──────────────────────────────────────────────────────────────────────
# Covers Vite's default ports (5173 / 5174) and CRA's port (3000).
# Add your production domain here before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",       # ← was missing — caused "Failed to fetch"
        "http://127.0.0.1:5174",       # ← was missing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ─────────────────────────────────────────────────────────────────
DISCLAIMER_TEXT = "This is not financial advice."
PINECONE_NAMESPACES = ("annual_reports", "news", "macro")
STOCK_CACHE_TTL_SECONDS = 3600
_stock_cache: dict[tuple[str, bool], tuple[float, dict[str, Any] | None]] = {}

PRICE_INTENT_PATTERNS = (
    r"\bprice\b",
    r"\bprices\b",
    r"\bhow\s+much\b",
    r"\bworth\b",
    r"\btrading\b",
    r"\bshare\b",
    r"\bshares\b",
    r"\brn\b",
    r"\bright\s+now\b",
    r"\bcurrent\b",
    r"\btoday\b",
    r"\bdividend\b",
    r"\bp/?e\b",
)
ANALYSIS_INTENT_PATTERNS = (
    r"\bwhy\b",
    r"\brisk\b",
    r"\banalysis\b",
    r"\bexplain\b",
    r"\boutlook\b",
    r"\bperformance\b",
)
COMPARE_INTENT_PATTERNS = (r"\bcompare\b", r"\bversus\b", r"\bvs\b")


# ── Request models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str


class CompareRequest(BaseModel):
    ticker1: str
    ticker2: str


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_cached_stock_data(
    ticker: str, include_history: bool = False
) -> dict[str, Any] | None:
    cache_key = (ticker.upper(), include_history)
    cached_item = _stock_cache.get(cache_key)
    if cached_item:
        cached_at, cached_payload = cached_item
        if time.time() - cached_at < STOCK_CACHE_TTL_SECONDS:
            return cached_payload

    # Get data from structured_data (uses yfinance with 3-sec timeout, falls back to seed)
    payload = await asyncio.to_thread(
        get_stock_data, ticker, include_history=include_history
    )
    
    if payload:
        _stock_cache[cache_key] = (time.time(), payload)
    
    return payload


async def _classify_query(user_query: str) -> str:
    lowered_query = user_query.lower()
    if any(re.search(p, lowered_query) for p in COMPARE_INTENT_PATTERNS):
        return "compare"
    if any(re.search(p, lowered_query) for p in PRICE_INTENT_PATTERNS):
        if not any(re.search(p, lowered_query) for p in ANALYSIS_INTENT_PATTERNS):
            return "price"
    return "analysis"


async def _query_namespace(namespace: str, query: str) -> list[dict]:
    try:
        return await asyncio.to_thread(
            query_documents,
            query,
            namespace=namespace,
            top_k=3,
        )
    except Exception:
        return []


async def _query_all_namespaces(query: str) -> list[dict]:
    namespace_results = await asyncio.gather(
        *[_query_namespace(ns, query) for ns in PINECONE_NAMESPACES]
    )
    matches: list[dict] = []
    for namespace, records in zip(PINECONE_NAMESPACES, namespace_results):
        for record in records:
            matches.append({**record, "namespace": namespace})
    return matches


def _build_structured_response(stock: dict[str, Any]) -> dict[str, Any]:
    price = stock.get("price")
    message = (
        f"{stock['name']} is trading at KES {price:.2f}."
        if price is not None
        else f"A live price for {stock['name']} is currently unavailable."
    )
    return {
        "type": "stock_info",
        "data": {
            "ticker": stock["ticker"],
            "name": stock["name"],
            "price": price,
            "history": stock.get("history", []),
            "pe_ratio": stock.get("pe_ratio"),
            "dividend_yield": stock.get("dividend_yield"),
            "source": stock.get("source", "fallback"),
        },
        "message": message,
        "disclaimer": DISCLAIMER_TEXT,
    }


async def _build_supported_prices_response(
    include_history: bool = False,
) -> dict[str, Any]:
    tickers = list(load_stock_data().keys())
    stocks = await asyncio.gather(
        *[_get_cached_stock_data(t, include_history=include_history) for t in tickers]
    )
    valid_stocks = [s for s in stocks if s]
    price_lines = [
        f"{s['name']} ({s['ticker']}): KES {s['price']:.2f} [{s.get('source', 'fallback')}]"
        for s in valid_stocks
        if s.get("price") is not None
    ]
    return {
        "type": "stock_list",
        "data": {"stocks": valid_stocks},
        "message": "Current supported NSE prices:\n" + "\n".join(price_lines),
        "disclaimer": DISCLAIMER_TEXT,
    }


def _format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def _format_ratio(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _format_currency(value: float | None) -> str:
    return "N/A" if value is None else f"KES {value:.2f}"


def _has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _trend_label(stock: dict[str, Any]) -> str:
    history = stock.get("history", [])
    if len(history) < 2:
        return "limited price-history signal"
    first_price = history[0].get("price")
    latest_price = history[-1].get("price")
    if first_price is None or latest_price is None:
        return "limited price-history signal"
    if latest_price > first_price:
        return "upward over the available period"
    if latest_price < first_price:
        return "downward over the available period"
    return "flat over the available period"


def _risk_level(stock: dict[str, Any]) -> str:
    ticker = stock.get("ticker", "").upper()
    pe_ratio = stock.get("pe_ratio")
    dividend_yield = stock.get("dividend_yield")
    if ticker == "KQ" or pe_ratio is None:
        return "High"
    if dividend_yield and dividend_yield >= 0.05:
        return "Moderate"
    return "Moderate to high"


def _build_local_analysis_message(
    user_query: str, stocks: list[dict[str, Any]]
) -> str:
    if not stocks:
        return (
            "I can analyse supported NSE counters such as Safaricom, KQ, Equity Group, "
            "or EABL. Please mention a specific counter so I can provide a grounded view."
        )
    stock = stocks[0]
    strengths, weaknesses = [], []
    dividend_yield = stock.get("dividend_yield")
    pe_ratio = stock.get("pe_ratio")

    if dividend_yield and dividend_yield > 0:
        strengths.append(f"a dividend yield of {_format_percent(dividend_yield)}")
    if pe_ratio is not None:
        strengths.append(f"a visible P/E ratio of {_format_ratio(pe_ratio)}")
    if not strengths:
        strengths.append("recognised NSE market presence")

    if stock.get("source") == "fallback":
        weaknesses.append("live yfinance data is unavailable, so this uses fallback data")
    if pe_ratio is None:
        weaknesses.append("valuation visibility is limited")
    if stock.get("ticker") == "KQ":
        weaknesses.append(
            "airline earnings can be volatile and sensitive to fuel, FX, and debt costs"
        )

    return (
        f"{stock['name']} ({stock['ticker']}) is shown at {_format_currency(stock.get('price'))} "
        f"using {stock.get('source', 'fallback')} data. Trend: {_trend_label(stock)}. "
        f"Risk level: {_risk_level(stock)}. Strengths include {', '.join(strengths)}. "
        f"Weaknesses include {', '.join(weaknesses)}. "
        "For a cautious NSE investor, treat this as a screening view and confirm live market data before acting."
    )


def _build_local_comparison_analysis(
    stocks: list[dict[str, Any]]
) -> str:
    if not stocks:
        return "No stocks provided for comparison."
    
    # Find best performer by highest dividend yield with non-null P/E ratio
    preferred = None
    max_yield = -1
    for stock in stocks:
        yield_val = stock.get("dividend_yield") or 0
        if yield_val > max_yield and stock.get("pe_ratio") is not None:
            max_yield = yield_val
            preferred = stock
    
    if not preferred:
        preferred = stocks[0]
    
    # Build comparison text for all stocks
    price_lines = []
    for stock in stocks:
        price_lines.append(
            f"{stock['ticker']}: {stock['name']} at {_format_currency(stock.get('price'))}"
        )
    
    metrics_lines = []
    for stock in stocks:
        metrics_lines.append(
            f"{stock['ticker']}: Trend {_trend_label(stock)}, Risk {_risk_level(stock)}, "
            f"Yield {_format_percent(stock.get('dividend_yield'))}, P/E {_format_ratio(stock.get('pe_ratio'))}"
        )
    
    return (
        "Prices: " + "; ".join(price_lines) + ". "
        "Trends & Risk: " + "; ".join(metrics_lines) + ". "
        "Weaknesses: fallback data should be confirmed against live NSE quotes before use. "
        f"Recommendation: {preferred['name']} ({preferred['ticker']}) looks more suitable for conservative screening based on available structured metrics."
    )


def _build_analysis_prompt(user_query: str, retrieved_context: str) -> str:
    context_preview = (retrieved_context[:800] + "..." if len(retrieved_context) > 800 else retrieved_context) if retrieved_context else "None"
    return f"""
Question: {user_query}

Context: {context_preview}

Analyze briefly in NSE context. Respond in under 150 words. Include disclaimer once.
""".strip()


def _build_comparison_prompt(
    user_query: str,
    stocks: list[dict[str, Any]],
    retrieved_context: str,
) -> str:
    context_preview = (retrieved_context[:800] + "..." if len(retrieved_context) > 800 else retrieved_context) if retrieved_context else "None"
    
    # Build labeled blocks for each stock
    labels = ['A', 'B', 'C', 'D']
    stock_blocks = []
    for i, stock in enumerate(stocks):
        label = labels[i] if i < len(labels) else chr(65 + i)
        stock_blocks.append(
            f"{label}: {stock['ticker']} - {stock['name']} - Price {_format_currency(stock.get('price'))}, "
            f"P/E {_format_ratio(stock.get('pe_ratio'))}, Yield {_format_percent(stock.get('dividend_yield'))}"
        )
    
    ticker_list = ", ".join([s['ticker'] for s in stocks])
    return f"""
Compare NSE counters: {ticker_list}

{chr(10).join(stock_blocks)}

Context: {context_preview}

Analyze all stocks in NSE context. Respond in under 150 words. Include disclaimer once.
""".strip()



def _to_sse(event: str, data: dict[str, Any] | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    payload = payload.replace("\n", "\ndata: ")
    return f"event: {event}\ndata: {payload}\n\n"


def _stream_sse_response(metadata: dict[str, Any], prompt: str) -> Iterator[str]:
    yield _to_sse("metadata", metadata)
    try:
        for chunk in generate_stream_response(prompt):
            yield _to_sse("token", chunk)
    except Exception:
        yield _to_sse(
            "token",
            (
                "I could not stream live AI analysis right now, but the structured NSE "
                "data response is still available. Please check your OpenAI configuration "
                "and try again.\n\nDisclaimer: This is not financial advice."
            ),
        )
    yield _to_sse("done", "[DONE]")


async def _build_compare_payload(
    tickers: list[str]
) -> dict[str, Any] | None:
    # Fetch all stocks in parallel
    stock_futures = [_get_cached_stock_data(t, include_history=True) for t in tickers]
    results = await asyncio.gather(
        *stock_futures,
        _query_all_namespaces(f"Compare {' and '.join(tickers)} on risk and performance"),
    )
    
    stocks = results[:-1]
    pinecone_matches = results[-1]
    
    # All stocks must be found
    if not all(stocks) or len(stocks) != len(tickers):
        return None
    
    # Build dynamic metrics dict for all tickers
    metrics = {
        "price": {},
        "pe_ratio": {},
        "dividend_yield": {},
    }
    for ticker, stock in zip(tickers, stocks):
        ticker_upper = ticker.upper()
        metrics["price"][ticker_upper] = stock["price"]
        metrics["pe_ratio"][ticker_upper] = stock.get("pe_ratio")
        metrics["dividend_yield"][ticker_upper] = stock.get("dividend_yield")
    
    scorecard = {
        "tickers": [t.upper() for t in tickers],
        "metrics": metrics,
        "analysis": _build_local_comparison_analysis(stocks),
    }
    return {
        "stocks": stocks,
        "scorecard": scorecard,
        "analysis": scorecard["analysis"],
        "retrieved_context": "\n".join(
            m["text"] for m in pinecone_matches if m.get("text")
        ),
    }



# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
async def home():
    return {"message": "NSE AI Advisor is running"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "services": {
            "api": True,
            "yfinance": get_stock_data is not None,
            "openai_sdk": llm_service.OpenAI is not None,
            "openai_key_loaded": bool(os.getenv("OPENAI_API_KEY")),
            "pinecone_sdk": pinecone_service.Pinecone is not None,
            "pinecone_key_loaded": bool(os.getenv("PINECONE_API_KEY")),
        },
    }


@app.get("/pinecone/status")
async def pinecone_status():
    try:
        counts = await asyncio.to_thread(
            get_namespace_counts,
            namespaces=("annual_reports", "macro", "news"),
        )
        return {"status": "ok", "namespaces": counts}
    except Exception as exc:
        return JSONResponse(
            {
                "status": "unavailable",
                "message": str(exc),
                "namespaces": {"annual_reports": 0, "macro": 0, "news": 0},
            },
            status_code=503,
        )


@app.get("/price/{ticker}")
async def price(ticker: str):
    stock = await _get_cached_stock_data(ticker, include_history=False)
    if not stock:
        return JSONResponse(
            {
                "type": "error",
                "data": {},
                "message": f"{ticker.upper()} is not currently supported.",
                "disclaimer": DISCLAIMER_TEXT,
            },
            status_code=404,
        )
    return _build_structured_response(stock)


@app.post("/compare")
async def compare(request: CompareRequest):
    payload = await _build_compare_payload(request.ticker1, request.ticker2)
    if not payload:
        return JSONResponse(
            {
                "type": "error",
                "data": {},
                "message": "One or both tickers are not currently supported.",
                "disclaimer": DISCLAIMER_TEXT,
            },
            status_code=404,
        )
    return {
        "type": "comparison",
        "data": {
            "stock1": payload["stock1"],
            "stock2": payload["stock2"],
            "scorecard": payload["scorecard"],
            "analysis": payload["analysis"],
        },
        "message": "Comparison data prepared.",
        "disclaimer": DISCLAIMER_TEXT,
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    tickers = extract_tickers(request.query)
    query_type = await _classify_query(request.query)

    # ── Price query ───────────────────────────────────────────────────────────
    if query_type == "price":
        if not tickers:
            return await _build_supported_prices_response(include_history=False)
        stock = await _get_cached_stock_data(tickers[0], include_history=False)
        if not stock:
            return JSONResponse(
                {
                    "type": "error",
                    "data": {},
                    "message": f"{tickers[0].upper()} is not currently supported.",
                    "disclaimer": DISCLAIMER_TEXT,
                },
                status_code=404,
            )
        return _build_structured_response(stock)

    # ── Compare query ─────────────────────────────────────────────────────────
    if query_type == "compare":
        if len(tickers) < 2 or len(tickers) > 4:
            return {
                "type": "error",
                "data": {},
                "message": "Please mention 2 to 4 NSE counters to compare.",
                "disclaimer": DISCLAIMER_TEXT,
            }
        payload = await _build_compare_payload(tickers)
        if not payload:
            return JSONResponse(
                {
                    "type": "error",
                    "data": {},
                    "message": "One or more tickers are not currently supported.",
                    "disclaimer": DISCLAIMER_TEXT,
                },
                status_code=404,
            )

        # No OpenAI key — return structured comparison only
        if not _has_openai_key():
            return {
                "type": "comparison",
                "data": {
                    "stocks": payload["stocks"],
                    "scorecard": payload["scorecard"],
                    "analysis": payload["analysis"],
                },
                "message": payload["analysis"],
                "disclaimer": DISCLAIMER_TEXT,
            }

        # No Pinecone context — return structured comparison with note
        if not payload["retrieved_context"]:
            return {
                "type": "comparison",
                "data": {
                    "stocks": payload["stocks"],
                    "scorecard": payload["scorecard"],
                    "analysis": payload["analysis"]
                    + " Document analysis is currently unavailable — Pinecone returned no relevant context.",
                },
                "message": payload["analysis"]
                + " Document analysis is currently unavailable — Pinecone returned no relevant context.",
                "disclaimer": DISCLAIMER_TEXT,
            }

        # Full streaming comparison
        metadata = {
            "type": "comparison",
            "data": {
                "stocks": payload["stocks"],
                "scorecard": payload["scorecard"],
                "analysis": payload["analysis"],
            },
            "message": "",
            "disclaimer": DISCLAIMER_TEXT,
        }
        prompt = _build_comparison_prompt(
            request.query,
            payload["stocks"],
            payload["retrieved_context"],
        )
        return StreamingResponse(
            _stream_sse_response(metadata, prompt),
            media_type="text/event-stream",
        )

        return StreamingResponse(
            _stream_sse_response(metadata, prompt),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # ── Analysis query ────────────────────────────────────────────────────────
    stocks, pinecone_matches = await asyncio.gather(
        asyncio.gather(*[_get_cached_stock_data(t, include_history=True) for t in tickers]),
        _query_all_namespaces(request.query),
    )
    valid_stocks = [s for s in stocks if s]
    retrieved_context = "\n".join(
        m["text"] for m in pinecone_matches if m.get("text")
    )

    if not _has_openai_key():
        return {
            "type": "ai_response",
            "data": {"tickers": tickers},
            "message": _build_local_analysis_message(request.query, valid_stocks),
            "disclaimer": DISCLAIMER_TEXT,
        }

    if not retrieved_context:
        return {
            "type": "ai_response",
            "data": {"tickers": tickers},
            "message": (
                _build_local_analysis_message(request.query, valid_stocks)
                + " Document analysis is currently unavailable — Pinecone returned no relevant context."
            ),
            "disclaimer": DISCLAIMER_TEXT,
        }

    metadata = {
        "type": "ai_response",
        "data": {"tickers": tickers},
        "message": "",
        "disclaimer": DISCLAIMER_TEXT,
    }
    prompt = _build_analysis_prompt(request.query, retrieved_context)
    return StreamingResponse(
        _stream_sse_response(metadata, prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )