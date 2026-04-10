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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DISCLAIMER_TEXT = "This is not financial advice."
PINECONE_NAMESPACES = ("annual_reports", "news", "macro")
STOCK_CACHE_TTL_SECONDS = 60
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


class ChatRequest(BaseModel):
    query: str


class CompareRequest(BaseModel):
    ticker1: str
    ticker2: str


async def _get_cached_stock_data(
    ticker: str, include_history: bool = False
) -> dict[str, Any] | None:
    cache_key = (ticker.upper(), include_history)
    cached_item = _stock_cache.get(cache_key)
    if cached_item:
        cached_at, cached_payload = cached_item
        if time.time() - cached_at < STOCK_CACHE_TTL_SECONDS:
            return cached_payload

    payload = await asyncio.to_thread(
        get_stock_data, ticker, include_history=include_history
    )
    _stock_cache[cache_key] = (time.time(), payload)
    return payload


async def _classify_query(user_query: str) -> str:
    lowered_query = user_query.lower()
    if any(re.search(pattern, lowered_query) for pattern in COMPARE_INTENT_PATTERNS):
        return "compare"
    if any(re.search(pattern, lowered_query) for pattern in PRICE_INTENT_PATTERNS):
        if not any(re.search(pattern, lowered_query) for pattern in ANALYSIS_INTENT_PATTERNS):
            return "price"

    classification = await asyncio.to_thread(classify_query, user_query)
    return classification.get("type", "analysis")


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
        *[_query_namespace(namespace, query) for namespace in PINECONE_NAMESPACES]
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


async def _build_supported_prices_response(include_history: bool = False) -> dict[str, Any]:
    tickers = list(load_stock_data().keys())
    stocks = await asyncio.gather(
        *[
            _get_cached_stock_data(ticker, include_history=include_history)
            for ticker in tickers
        ]
    )
    valid_stocks = [stock for stock in stocks if stock]
    price_lines = [
        f"{stock['name']} ({stock['ticker']}): KES {stock['price']:.2f} [{stock.get('source', 'fallback')}]"
        for stock in valid_stocks
    ]
    return {
        "type": "stock_list",
        "data": {"stocks": valid_stocks},
        "message": "Current supported NSE prices:\n" + "\n".join(price_lines),
        "disclaimer": DISCLAIMER_TEXT,
    }


def _format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def _format_currency(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"KES {value:.2f}"


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


def _build_local_analysis_message(user_query: str, stocks: list[dict[str, Any]]) -> str:
    if not stocks:
        return (
            "I can analyse supported NSE counters such as Safaricom, KQ, Equity Group, "
            "or EABL. Please mention a specific counter so I can provide a grounded view."
        )

    stock = stocks[0]
    strengths = []
    weaknesses = []
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
        weaknesses.append("airline earnings can be volatile and sensitive to fuel, FX, and debt costs")

    return (
        f"{stock['name']} ({stock['ticker']}) is shown at {_format_currency(stock.get('price'))} "
        f"using {stock.get('source', 'fallback')} data. Trend: {_trend_label(stock)}. "
        f"Risk level: {_risk_level(stock)}. Strengths include {', '.join(strengths)}. "
        f"Weaknesses include {', '.join(weaknesses)}. "
        "For a cautious NSE investor, treat this as a screening view and confirm live market data before acting."
    )


def _build_local_comparison_analysis(stock1: dict[str, Any], stock2: dict[str, Any]) -> str:
    dividend1 = stock1.get("dividend_yield") or 0
    dividend2 = stock2.get("dividend_yield") or 0
    preferred = stock1 if dividend1 >= dividend2 and stock1.get("pe_ratio") is not None else stock2

    return (
        f"{stock1['name']} trades at {_format_currency(stock1.get('price'))}, while "
        f"{stock2['name']} trades at {_format_currency(stock2.get('price'))}. "
        f"Trend: {stock1['ticker']} is {_trend_label(stock1)}; {stock2['ticker']} is {_trend_label(stock2)}. "
        f"Risk level: {stock1['ticker']} is {_risk_level(stock1)}; {stock2['ticker']} is {_risk_level(stock2)}. "
        f"Strengths: {stock1['ticker']} has dividend yield {_format_percent(stock1.get('dividend_yield'))} "
        f"and P/E {_format_ratio(stock1.get('pe_ratio'))}; {stock2['ticker']} has dividend yield "
        f"{_format_percent(stock2.get('dividend_yield'))} and P/E {_format_ratio(stock2.get('pe_ratio'))}. "
        "Weaknesses: fallback data should be confirmed against live NSE quotes before use. "
        f"Recommendation: {preferred['name']} looks more suitable for conservative screening based on available structured metrics."
    )


def _build_analysis_prompt(user_query: str, retrieved_context: str) -> str:
    return f"""
Question: {user_query}

Retrieved context from Pinecone:
{retrieved_context or "No Pinecone context was available."}

Write a concise, professional response in an NSE-focused financial analyst tone.
Use the context where relevant. If context is limited, say so briefly.
Include trend, risk level, strengths, and weaknesses where possible.
Keep the answer under 200 tokens and include the disclaimer exactly once.
""".strip()


def _build_comparison_prompt(
    user_query: str,
    stock1: dict[str, Any],
    stock2: dict[str, Any],
    retrieved_context: str,
) -> str:
    return f"""
Question: {user_query}

Stock A: {stock1['name']} ({stock1['ticker']})
- Price: {_format_currency(stock1.get('price'))}
- P/E ratio: {_format_ratio(stock1.get('pe_ratio'))}
- Dividend yield: {_format_percent(stock1.get('dividend_yield'))}

Stock B: {stock2['name']} ({stock2['ticker']})
- Price: {_format_currency(stock2.get('price'))}
- P/E ratio: {_format_ratio(stock2.get('pe_ratio'))}
- Dividend yield: {_format_percent(stock2.get('dividend_yield'))}

Retrieved context from Pinecone:
{retrieved_context or "No Pinecone context was available."}

Write a concise NSE-focused comparison with:
1. strengths
2. weaknesses
3. trend and risk level
4. recommendation
Keep the answer under 200 tokens and include the disclaimer exactly once.
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


async def _build_compare_payload(ticker1: str, ticker2: str) -> dict[str, Any] | None:
    stock1, stock2, pinecone_matches = await asyncio.gather(
        _get_cached_stock_data(ticker1, include_history=True),
        _get_cached_stock_data(ticker2, include_history=True),
        _query_all_namespaces(f"Compare {ticker1} and {ticker2} on risk and performance"),
    )

    if not stock1 or not stock2:
        return None

    scorecard = {
        "ticker1": ticker1.upper(),
        "ticker2": ticker2.upper(),
        "metrics": {
            "price": {
                ticker1.upper(): stock1["price"],
                ticker2.upper(): stock2["price"],
            },
            "pe_ratio": {
                ticker1.upper(): stock1.get("pe_ratio"),
                ticker2.upper(): stock2.get("pe_ratio"),
            },
            "dividend_yield": {
                ticker1.upper(): stock1.get("dividend_yield"),
                ticker2.upper(): stock2.get("dividend_yield"),
            },
        },
        "analysis": _build_local_comparison_analysis(stock1, stock2),
    }

    return {
        "stock1": stock1,
        "stock2": stock2,
        "scorecard": scorecard,
        "analysis": scorecard["analysis"],
        "retrieved_context": "\n".join(
            match["text"] for match in pinecone_matches if match.get("text")
        ),
    }


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

    if query_type == "compare":
        if len(tickers) < 2:
            return {
                "type": "error",
                "data": {},
                "message": "Please mention two NSE counters to compare.",
                "disclaimer": DISCLAIMER_TEXT,
            }

        payload = await _build_compare_payload(tickers[0], tickers[1])
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

        metadata = {
            "type": "comparison",
            "data": {
                "stock1": payload["stock1"],
                "stock2": payload["stock2"],
                "scorecard": payload["scorecard"],
                "analysis": payload["analysis"],
            },
            "message": "",
            "disclaimer": DISCLAIMER_TEXT,
        }
        if not _has_openai_key():
            return {
                "type": "comparison",
                "data": {
                    "stock1": payload["stock1"],
                    "stock2": payload["stock2"],
                    "scorecard": payload["scorecard"],
                    "analysis": payload["analysis"],
                },
                "message": payload["analysis"],
                "disclaimer": DISCLAIMER_TEXT,
            }
        prompt = _build_comparison_prompt(
            request.query,
            payload["stock1"],
            payload["stock2"],
            payload["retrieved_context"],
        )
        if not payload["retrieved_context"]:
            return {
                "type": "comparison",
                "data": {
                    "stock1": payload["stock1"],
                    "stock2": payload["stock2"],
                    "scorecard": payload["scorecard"],
                    "analysis": (
                        payload["analysis"]
                        + " Document analysis is currently unavailable because Pinecone returned no relevant annual-report context."
                    ),
                },
                "message": payload["analysis"]
                + " Document analysis is currently unavailable because Pinecone returned no relevant annual-report context.",
                "disclaimer": DISCLAIMER_TEXT,
            }
        return StreamingResponse(
            _stream_sse_response(metadata, prompt),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    stocks = await asyncio.gather(
        *[_get_cached_stock_data(ticker, include_history=True) for ticker in tickers]
    )
    valid_stocks = [stock for stock in stocks if stock]
    if not _has_openai_key():
        return {
            "type": "ai_response",
            "data": {"tickers": tickers},
            "message": _build_local_analysis_message(request.query, valid_stocks),
            "disclaimer": DISCLAIMER_TEXT,
        }

    pinecone_matches = await _query_all_namespaces(request.query)
    retrieved_context = "\n".join(
        match["text"] for match in pinecone_matches if match.get("text")
    )
    if not retrieved_context:
        return {
            "type": "ai_response",
            "data": {"tickers": tickers},
            "message": (
                _build_local_analysis_message(request.query, valid_stocks)
                + " Document analysis is currently unavailable because Pinecone returned no relevant annual-report context."
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
