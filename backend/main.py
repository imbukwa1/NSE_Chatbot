import asyncio
import json
import logging
import os
import re
import time
import inspect
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
load_dotenv(BASE_DIR / ".env.example")

import database
import intent_router
import news as news_module

from services.advisor_logic import extract_tickers
from services import llm_service, pinecone_service
from services.llm_service import classify_query, generate_stream_response
from services.pinecone_service import get_namespace_counts, query_documents
from services.structured_data import get_all_stock_data, get_stock_data, load_stock_data
from services.market_intelligence import (
    build_market_overview_message,
    build_portfolio_payload,
    get_market_overview,
    stocks_by_sector,
)
from services.market_cache import EAT
from routes.auth_routes import router as auth_router
from routes.admin_routes import router as admin_router
from routes.analytics_routes import router as analytics_router
from routes.chat_routes import router as chat_history_router
from routes.dashboard_routes import router as dashboard_router
from routes.favorites_routes import router as favorites_router
from routes.market_routes import router as market_router
from routes.profile_routes import router as profile_router
from routes.system_routes import router as system_router
from routes.watchlist_routes import router as watchlist_router
from services.scheduler import register_market_scrape_jobs
from services.scraper import scrape_and_update_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(chat_history_router)
app.include_router(profile_router)
app.include_router(favorites_router)
app.include_router(watchlist_router)
app.include_router(market_router)
app.include_router(dashboard_router)
app.include_router(system_router)

database.init_db()

scheduler = BackgroundScheduler()


def scrape_and_cache(snapshot_label: str = "manual"):
    return scrape_and_update_cache(snapshot_label)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting background scheduler")
    register_market_scrape_jobs(scheduler)
    scheduler.start()
    logger.info("Scheduler started with fixed daily NSE scraper jobs")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down scheduler")
    if scheduler.running:
        scheduler.shutdown()
    logger.info("Scheduler shut down")

# ── CORS ──────────────────────────────────────────────────────────────────────
# Covers Vite's default ports (5173 / 5174) and CRA's port (3000).
# Add production domains through FRONTEND_ORIGINS before deploying.
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
]
configured_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",       # ← was missing — caused "Failed to fetch"
        "http://127.0.0.1:5174",       # ← was missing
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ─────────────────────────────────────────────────────────────────
DISCLAIMER_TEXT = "This is not financial advice."
PINECONE_NAMESPACES = ("annual_reports", "news", "macro")
STOCK_CACHE_TTL_SECONDS = 900
_stock_cache: dict[tuple[str, bool], tuple[float, dict[str, Any] | None]] = {}

PRICE_INTENT_PATTERNS = (
    r"\bprice\b",
    r"\bprices\b",
    r"\bprizes\b",
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
TREND_INTENT_PATTERNS = (
    r"\btrend\b",
    r"\btrends\b",
    r"\btrens\b",
    r"\bhistorical\b",
    r"\bhistory\b",
    r"\bover\s+\d+\s+(day|days|week|weeks|month|months|year|years)\b",
    r"\b(last|past)\s+\d+\s+(day|days|week|weeks|month|months|year|years)\b",
    r"\b\d+\s*(d|day|days|w|wk|wks|week|weeks|m|mo|mos|month|months|y|yr|yrs|year|years)\b",
)
ANALYSIS_INTENT_PATTERNS = (
    r"\bwhy\b",
    r"\brisk\b",
    r"\banalysis\b",
    r"\bexplain\b",
    r"\boutlook\b",
    r"\bperformance\b",
    *TREND_INTENT_PATTERNS,
)
COMPARE_INTENT_PATTERNS = (r"\bcompare\b", r"\bversus\b", r"\bvs\b")
ADVICE_INTENT_PATTERNS = (
    r"\binvest\b",
    r"\bbuy\b",
    r"\bsell\b",
    r"\brecommend\b",
    r"\bshould\s+i\b",
    r"\bwhich\s+company\b",
)
NEWS_INTENT_PATTERNS = (
    r"\bnews\b",
    r"\blatest\b",
    r"\brecent\b",
    r"\bupdate\b",
    r"\bannouncement\b",
)
MARKET_OVERVIEW_PATTERNS = (
    r"\bmarket\s+summary\b",
    r"\bsummarize\s+today",
    r"\btoday'?s\s+nse\b",
    r"\bmarket\s+status\b",
    r"\bopen\s+or\s+closed\b",
    r"\btop\s+gainers?\b",
    r"\btop\s+losers?\b",
    r"\bmost\s+active\b",
    r"\bhighest\s+dividend\b",
    r"\bdividend\s+yield\b",
)
PORTFOLIO_PATTERNS = (
    r"\bi\s+own\b",
    r"\bmy\s+portfolio\b",
    r"\bholdings?\b",
    r"\bi\s+hold\b",
)
FUNDAMENTAL_INTENT_PATTERNS = (
    r"\bfundamental\b",
    r"\bvaluation\b",
    r"\bp/?e\b",
    r"\bearnings\b",
    r"\beps\b",
)
BEGINNER_QUESTION_PATTERNS = (
    r"\bwhat\s+is\b",
    r"\bwhat\s+are\b",
    r"\bmeaning\s+of\b",
    r"\bdefine\b",
    r"\bexplain\b",
    r"\bteach\s+me\b",
    r"\bhow\s+does\b",
    r"\bhow\s+do\b",
)
BEGINNER_TOPICS = {
    "dividend": (
        "A dividend is part of a company's profit paid to shareholders. "
        "For example, if you own shares in a company and it declares a dividend, "
        "you may receive cash based on how many shares you own. On the NSE, dividends "
        "usually have key dates: declaration date, book closure date, and payment date. "
        "Dividend yield compares the dividend to the share price, helping investors "
        "estimate income potential."
    ),
    "share": (
        "A share is a small ownership unit in a company. When you buy shares of an "
        "NSE-listed company, you own a small part of that company. You can benefit if "
        "the share price rises, and some companies may also pay dividends."
    ),
    "stock": (
        "A stock represents ownership in a listed company. In everyday NSE language, "
        "people often use stock and share to mean almost the same thing."
    ),
    "bond": (
        "A bond is a loan made by investors to a government or company. The issuer "
        "normally pays interest over time and repays the principal at maturity. Bonds "
        "are generally different from shares because they focus more on fixed income "
        "than company ownership."
    ),
    "ipo": (
        "An IPO, or Initial Public Offering, is when a company sells shares to the "
        "public for the first time. After listing, those shares can trade on an "
        "exchange such as the NSE."
    ),
    "p/e": (
        "The P/E ratio, or price-to-earnings ratio, compares a company's share price "
        "with its earnings per share. It helps investors judge whether a stock looks "
        "expensive or cheap compared with its profits, though it should not be used alone."
    ),
    "eps": (
        "EPS means earnings per share. It shows how much profit a company made for "
        "each ordinary share. Rising EPS can suggest improving profitability."
    ),
    "market cap": (
        "Market capitalization is the total market value of a listed company. It is "
        "calculated as share price multiplied by the number of shares. It helps compare "
        "company size."
    ),
    "cds": (
        "A CDS account is the account used to hold securities such as shares in Kenya. "
        "To buy NSE shares, investors normally open a CDS account through an approved "
        "stockbroker or investment bank."
    ),
}
TYPO_NORMALIZATIONS = (
    (r"\bdividence\b", "dividend"),
    (r"\bdivident\b", "dividend"),
    (r"\bdividance\b", "dividend"),
    (r"\bdividents\b", "dividends"),
)


# ── Request models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str


class CompareRequest(BaseModel):
    ticker1: str | None = None
    ticker2: str | None = None
    tickers: list[str] | None = None


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


def _extract_timeframe(lowered_query: str) -> str | None:
    match = re.search(
        r"\b(?:over|last|past)?\s*(\d+)\s*(day|days|week|weeks|month|months|year|years|d|w|wk|wks|m|mo|mos|y|yr|yrs)\b",
        lowered_query,
    )
    if not match:
        return None
    amount, unit = match.groups()
    unit_map = {
        "d": "days",
        "day": "days",
        "w": "weeks",
        "wk": "weeks",
        "wks": "weeks",
        "week": "weeks",
        "m": "months",
        "mo": "months",
        "mos": "months",
        "month": "months",
        "y": "years",
        "yr": "years",
        "yrs": "years",
        "year": "years",
    }
    normalized = unit_map.get(unit, unit)
    return f"{amount} {normalized}"


def _normalize_user_query(user_query: str) -> str:
    normalized = user_query
    for pattern, replacement in TYPO_NORMALIZATIONS:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized


def _is_beginner_question(lowered_query: str, tickers: list[str] | None = None) -> bool:
    if tickers:
        return False
    has_beginner_phrase = any(
        re.search(pattern, lowered_query) for pattern in BEGINNER_QUESTION_PATTERNS
    )
    has_known_topic = any(topic in lowered_query for topic in BEGINNER_TOPICS)
    return has_beginner_phrase and has_known_topic


def _topic_from_query(lowered_query: str) -> str:
    for topic in BEGINNER_TOPICS:
        if topic in lowered_query:
            return topic
    return "general investing"


def _build_local_education_response(user_query: str) -> dict[str, Any]:
    lowered_query = _normalize_user_query(user_query).lower()
    topic = _topic_from_query(lowered_query)
    explanation = BEGINNER_TOPICS.get(
        topic,
        "This is an investing education question. Ask about terms like dividends, "
        "shares, bonds, IPOs, P/E ratio, EPS, market cap, or CDS accounts.",
    )
    return {
        "type": "educational",
        "data": {"topic": topic},
        "message": explanation,
        "disclaimer": DISCLAIMER_TEXT,
    }


async def _classify_query(user_query: str) -> dict[str, Any]:
    """
    Classify a query using Featherless intent routing.
    Falls back to local rules if no chat provider is available.
    """
    normalized_query = _normalize_user_query(user_query)
    lowered_query = normalized_query.lower()
    if _is_beginner_question(lowered_query, extract_tickers(normalized_query)):
        return {"intent": "learn_mode", "entity": _topic_from_query(lowered_query), "timeframe": None}
    if any(re.search(p, lowered_query) for p in COMPARE_INTENT_PATTERNS):
        return {"intent": "compare", "entity": None, "timeframe": None}
    if any(re.search(p, lowered_query) for p in MARKET_OVERVIEW_PATTERNS):
        return {"intent": "market_overview", "entity": None, "timeframe": "current"}
    if any(re.search(p, lowered_query) for p in TREND_INTENT_PATTERNS):
        return {"intent": "stock_summary", "entity": None, "timeframe": _extract_timeframe(lowered_query)}
    if any(re.search(p, lowered_query) for p in PRICE_INTENT_PATTERNS):
        if not any(re.search(p, lowered_query) for p in ANALYSIS_INTENT_PATTERNS):
            return {"intent": "price_lookup", "entity": None, "timeframe": None}
    if any(re.search(p, lowered_query) for p in NEWS_INTENT_PATTERNS):
        return {"intent": "news", "entity": None, "timeframe": "recent"}
    if any(re.search(p, lowered_query) for p in ADVICE_INTENT_PATTERNS):
        return {"intent": "ai_advice", "entity": None, "timeframe": None}
    if any(re.search(p, lowered_query) for p in FUNDAMENTAL_INTENT_PATTERNS):
        return {"intent": "fundamentals", "entity": None, "timeframe": None}

    if not _has_ai_provider():
        # Fallback to regex-based classification if no AI provider is configured.
        return {"intent": "ai_advice", "entity": None, "timeframe": None}

    classification = intent_router.classify(normalized_query)
    if inspect.isawaitable(classification):
        classification = await classification

    if hasattr(classification, "to_dict"):
        classification = classification.to_dict()

    if not isinstance(classification, dict):
        return {"intent": "ai_advice", "entity": None, "timeframe": None}

    if classification.get("type") == "analysis":
        return {"intent": "ai_advice", "entity": None, "timeframe": None}
    if classification.get("type") == "price":
        return {"intent": "price_lookup", "entity": None, "timeframe": None}

    return classification


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
    change = stock.get("change_pct")
    if isinstance(change, (int, float)) and change > 0:
        movement = f", up {change:.2f}% today"
    elif isinstance(change, (int, float)) and change < 0:
        movement = f", down {abs(change):.2f}% today"
    else:
        movement = ""
    updated = stock.get("last_updated") or stock.get("updated_at") or "latest cached snapshot"
    source = stock.get("source", "sqlite_cache")
    message = (
        f"{stock['name']} ({stock['ticker']}) is currently trading at KES {price:.2f}{movement}.\n\n"
        f"Last updated: {updated}\nSource: {source}"
        if price is not None
        else (
            f"A cached price for {stock['name']} is currently unavailable.\n\n"
            f"Last updated: {updated}\nSource: {source}"
        )
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
            "source": source,
            "last_updated": updated,
            "market_status": stock.get("market_status"),
        },
        "message": message,
        "disclaimer": DISCLAIMER_TEXT,
    }


async def _build_supported_prices_response(
    include_history: bool = False,
) -> dict[str, Any]:
    stocks = await asyncio.to_thread(
        get_all_stock_data, include_history=include_history
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


def _is_configured_secret(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    if not normalized:
        return False
    placeholder_tokens = (
        "your_",
        "your-",
        "replace",
        "placeholder",
        "example",
        "test_key",
        "api_key_here",
    )
    return not any(token in normalized for token in placeholder_tokens)


def _has_openai_key() -> bool:
    # Backward-compatible name used throughout older route logic.
    return _has_ai_provider()


def _has_ai_provider() -> bool:
    return llm_service.has_chat_provider()


def _parse_history_point(point: dict[str, Any]) -> tuple[str | None, float | None]:
    price = point.get("price")
    try:
        price_value = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_value = None
    return point.get("date"), price_value


def _build_trend_analysis_message(
    user_query: str,
    stock: dict[str, Any],
    timeframe: str | None = None,
) -> str:
    history = stock.get("history") or []
    valid_points = [
        {"date": date, "price": price}
        for date, price in (_parse_history_point(point) for point in history)
        if date and price is not None
    ]

    if len(valid_points) < 2:
        return (
            f"{stock['name']} ({stock['ticker']}) is shown at {_format_currency(stock.get('price'))}, "
            "but I do not have enough historical price points connected right now to calculate a reliable trend. "
            f"Source: {stock.get('source', 'fallback')}. Confirm live NSE data before acting."
        )

    first = valid_points[0]
    latest = valid_points[-1]
    first_price = first["price"]
    latest_price = latest["price"]
    absolute_change = latest_price - first_price
    percent_change = (absolute_change / first_price) * 100 if first_price else 0
    high = max(valid_points, key=lambda point: point["price"])
    low = min(valid_points, key=lambda point: point["price"])

    direction = "up" if absolute_change > 0 else "down" if absolute_change < 0 else "flat"
    requested = timeframe or _extract_timeframe(user_query.lower())
    period_label = f"the requested {requested}" if requested else "the available period"
    coverage_note = (
        f"Available chart data runs from {first['date']} to {latest['date']}; "
        f"use that coverage as the basis for this answer, even if you asked for {requested}."
        if requested
        else f"Available chart data runs from {first['date']} to {latest['date']}."
    )

    return (
        f"{stock['name']} ({stock['ticker']}) trend over {period_label}: {direction}. "
        f"It moved from {_format_currency(first_price)} on {first['date']} to "
        f"{_format_currency(latest_price)} on {latest['date']} "
        f"({_format_currency(absolute_change)}, {percent_change:.2f}%). "
        f"Range: high {_format_currency(high['price'])} on {high['date']}, "
        f"low {_format_currency(low['price'])} on {low['date']}. "
        f"Current snapshot: {_format_currency(stock.get('price'))}, P/E {_format_ratio(stock.get('pe_ratio'))}, "
        f"dividend yield {_format_percent(stock.get('dividend_yield'))}. "
        f"{coverage_note} Source: {stock.get('source', 'fallback')}. "
        "This is a screening view, not financial advice."
    )


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

    macro_note = ""
    if re.search(r"\b(government|govt|policy|tax|election|budget|rate|inflation|news)\b", user_query.lower()):
        macro_note = (
            " Macro/news factors such as government policy, taxes, interest rates, "
            "inflation, and sector regulation can change the risk view quickly, so "
            "confirm recent headlines before acting."
        )

    return (
        f"{stock['name']} ({stock['ticker']}) is shown at {_format_currency(stock.get('price'))} "
        f"using {stock.get('source', 'fallback')} data. Trend: {_trend_label(stock)}. "
        f"Risk level: {_risk_level(stock)}. Strengths include {', '.join(strengths)}. "
        f"Weaknesses include {', '.join(weaknesses)}. "
        f"{macro_note} "
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
        "Macro/news watch: changes in government policy, taxes, rates, inflation, sector regulation, and company news can shift the ranking. "
        "Weaknesses: fallback data should be confirmed against live NSE quotes before use. "
        f"Recommendation: {preferred['name']} ({preferred['ticker']}) looks more suitable for conservative screening based on available structured metrics."
    )


def _rank_market_stocks(stocks: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    def score(stock: dict[str, Any]) -> float:
        pe_ratio = stock.get("pe_ratio")
        dividend_yield = stock.get("dividend_yield") or 0
        change_pct = stock.get("change_pct") or 0
        pe_score = 0
        if isinstance(pe_ratio, (int, float)) and pe_ratio > 0:
            pe_score = max(0, 20 - pe_ratio) / 20
        return (dividend_yield * 8) + pe_score + (change_pct / 100)

    return sorted(
        [s for s in stocks if s.get("price") is not None],
        key=score,
        reverse=True,
    )[:limit]


def _build_market_recommendation_message(
    user_query: str,
    stocks: list[dict[str, Any]],
    news_summary: str = "",
) -> str:
    if not stocks:
        return (
            "I could not fetch enough NSE market data to rank companies right now. "
            "Please ask about a specific counter or try again shortly."
        )

    ranked = _rank_market_stocks(stocks)
    lines = [
        (
            f"{index}. {stock['name']} ({stock['ticker']}): "
            f"{_format_currency(stock.get('price'))}, P/E {_format_ratio(stock.get('pe_ratio'))}, "
            f"yield {_format_percent(stock.get('dividend_yield'))}, "
            f"change {stock.get('change_pct', 'N/A')}%, source {stock.get('source', 'fallback')}"
        )
        for index, stock in enumerate(ranked, 1)
    ]

    news_note = ""
    if news_summary:
        news_note = (
            " Recent market news considered: "
            + " ".join(news_summary.split())[:500]
            + "."
        )

    month_note = (
        " For May, I would screen defensively: prefer liquid, profitable counters "
        "with visible dividends and watch government policy, budget/tax changes, "
        "interest rates, inflation, FX, and sector regulation."
    )

    return (
        "Based on the latest available NSE price feed/fallback dataset, my shortlist is:\n"
        + "\n".join(lines)
        + "\n\n"
        + month_note
        + news_note
        + " This is a screening view, not a buy instruction; confirm live NSE quotes and recent announcements before investing."
    )


def _build_analysis_prompt(user_query: str, retrieved_context: str) -> str:
    context_preview = (retrieved_context[:800] + "..." if len(retrieved_context) > 800 else retrieved_context) if retrieved_context else "None"
    return f"""
Question: {user_query}

Context: {context_preview}

Analyze briefly in NSE context. Use current price context, company fundamentals, and recent news when available. Discuss government policy, budget/tax changes, rates, inflation, FX, and sector regulation if relevant. Respond in under 180 words. Include disclaimer once.
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

Analyze all stocks in NSE context. Include price, valuation, dividend yield, trend, risk, and relevant macro/news factors such as government policy, taxes, rates, inflation, and sector regulation. Respond in under 150 words. Include disclaimer once.
""".strip()


def _build_price_news_analysis_prompt(
    user_query: str,
    ticker: str,
    price_data: dict[str, Any] | None,
    news_summary: str,
) -> str:
    """Build prompt for analyzing price movement given news context."""
    price_info = "No price data available."
    if price_data:
        price_info = (
            f"{ticker} currently trading at {_format_currency(price_data.get('price'))}, "
            f"Change: {_format_percent(price_data.get('change_pct'))} "
            f"(P/E: {_format_ratio(price_data.get('pe_ratio'))}, "
            f"Dividend Yield: {_format_percent(price_data.get('dividend_yield'))})"
        )

    return f"""
Analyze this price movement given the news context. Always add: This is not financial advice.

Stock: {ticker}
{price_info}

Recent News:
{news_summary}

Question: {user_query}

Provide brief NSE-focused analysis (under 150 words) connecting the price movement to the news context.
Remind the user this is not financial advice.
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
                "data response is still available. Please check your Featherless configuration "
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
            "openai_compatible_sdk": llm_service.OpenAI is not None,
            "ai_provider": llm_service.get_provider_settings()["provider"],
            "featherless_key_loaded": _has_ai_provider(),
            "pinecone_sdk": pinecone_service.Pinecone is not None,
            "pinecone_key_loaded": _is_configured_secret(os.getenv("PINECONE_API_KEY")),
            "newsapi_key_loaded": _is_configured_secret(os.getenv("NEWSAPI_KEY")),
            "env_file_present": (BASE_DIR / ".env").exists(),
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


@app.get("/api/stocks")
async def get_stocks_from_db():
    """Get all stocks from SQLite database (never scrapes live on request)."""
    try:
        stocks = await asyncio.to_thread(database.get_all_stocks)
        last_update = await asyncio.to_thread(database.get_last_update_time)

        return {
            "status": "success",
            "data": stocks,
            "last_updated": last_update,
            "count": len(stocks),
            "timestamp": datetime.now().isoformat(),
            "source": "sqlite_cache",
        }
    except Exception as e:
        logger.error(f"Error fetching stocks from database: {e}")
        return JSONResponse(
            {
                "status": "error",
                "message": str(e),
                "data": [],
                "count": 0,
            },
            status_code=500,
        )


@app.get("/api/stocks/{ticker}")
async def get_stock_from_db(ticker: str):
    """Get a specific stock from SQLite database by ticker."""
    try:
        stock = await asyncio.to_thread(database.get_stock_by_ticker, ticker)

        if not stock:
            return JSONResponse(
                {
                    "status": "not_found",
                    "message": f"Ticker {ticker.upper()} not found in database",
                    "data": None,
                },
                status_code=404,
            )

        history = await asyncio.to_thread(database.get_price_history, ticker, 30)

        return {
            "status": "success",
            "data": {**stock, "price_history": history},
            "timestamp": datetime.now().isoformat(),
            "source": "sqlite_cache",
        }
    except Exception as e:
        logger.error(f"Error fetching stock {ticker} from database: {e}")
        return JSONResponse(
            {
                "status": "error",
                "message": str(e),
                "data": None,
            },
            status_code=500,
        )


@app.get("/scraper/status")
async def scraper_status():
    """Check scraper and database status."""
    try:
        last_update = await asyncio.to_thread(database.get_last_update_time)
        stock_count = len(await asyncio.to_thread(database.get_all_stocks))

        return {
            "status": "running" if scheduler.running else "stopped",
            "scheduler_active": scheduler.running,
            "database_populated": stock_count > 0,
            "stock_count": stock_count,
            "last_database_update": last_update,
            "current_time_eat": datetime.now(EAT).isoformat(),
            "scrape_schedule": "Daily snapshots at 09:00, 12:00, and 15:00 EAT",
        }
    except Exception as e:
        logger.error(f"Error getting scraper status: {e}")
        return JSONResponse(
            {
                "status": "error",
                "message": str(e),
            },
            status_code=500,
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
    tickers = request.tickers or [request.ticker1, request.ticker2]
    tickers = [ticker for ticker in tickers if ticker]
    if len(tickers) < 2:
        return JSONResponse(
            {
                "type": "error",
                "data": {},
                "message": "Please mention at least two NSE counters to compare.",
                "disclaimer": DISCLAIMER_TEXT,
            },
            status_code=400,
        )

    payload = await _build_compare_payload(tickers)
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
            "stocks": payload["stocks"],
            "scorecard": payload["scorecard"],
            "analysis": payload["analysis"],
        },
        "message": "Comparison data prepared.",
        "disclaimer": DISCLAIMER_TEXT,
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    normalized_query = _normalize_user_query(request.query)
    tickers = extract_tickers(normalized_query)
    lowered_query = normalized_query.lower()
    wants_market_list = bool(
        re.search(r"\b(all|every|list)\b", lowered_query)
        and re.search(
            r"\b(companies|counters|stocks|shares|prices)\b",
            lowered_query,
        )
    )

    if any(re.search(pattern, lowered_query) for pattern in PORTFOLIO_PATTERNS):
        portfolio = await asyncio.to_thread(build_portfolio_payload, normalized_query)
        if portfolio:
            return {
                "type": "portfolio",
                "data": portfolio,
                "message": (
                    f"Current portfolio value is KES {portfolio['summary']['total_value']:,.2f}. "
                    f"Estimated annual dividends are KES {portfolio['summary']['estimated_annual_dividends']:,.2f}."
                ),
                "disclaimer": DISCLAIMER_TEXT,
            }

    if re.search(r"\b(bank|banks|banking)\b", lowered_query) and re.search(
        r"\b(listed|which|show|all)\b", lowered_query
    ):
        bank_stocks = await asyncio.to_thread(stocks_by_sector, "Banking")
        return {
            "type": "stock_list",
            "data": {"stocks": bank_stocks, "title": "Listed Banks"},
            "message": f"I found {len(bank_stocks)} banking counters in the supported NSE dataset.",
            "disclaimer": DISCLAIMER_TEXT,
        }

    classification = await _classify_query(normalized_query)
    intent = classification.get("intent", "ai_advice")
    entity = classification.get("entity")
    timeframe = classification.get("timeframe")

    if intent == "market_overview":
        overview = await asyncio.to_thread(get_market_overview)
        if re.search(r"\b(highest|best|top)\b", lowered_query) and re.search(
            r"\bdividend|yield\b", lowered_query
        ):
            return {
                "type": "stock_list",
                "data": {
                    "stocks": overview["dividend_leaders"],
                    "title": "Highest Dividend Yield",
                },
                "message": "These counters have the highest dividend yields in the supported dataset.",
                "disclaimer": DISCLAIMER_TEXT,
            }
        return {
            "type": "market_overview",
            "data": overview,
            "message": build_market_overview_message(overview),
            "disclaimer": DISCLAIMER_TEXT,
        }

    # ── PRICE_LOOKUP: Show current price for specific stock ──────────────────
    if intent == "price_lookup":
        if not tickers or wants_market_list:
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

    # ── DIVIDEND_INFO: Show dividend yield and history ──────────────────────
    if intent == "dividend_info":
        if not tickers:
            return {
                "type": "error",
                "data": {},
                "message": "Please mention a specific stock to see dividend information.",
                "disclaimer": DISCLAIMER_TEXT,
            }
        stock = await _get_cached_stock_data(tickers[0], include_history=True)
        if not stock:
            return JSONResponse(
                {
                    "type": "error",
                    "data": {},
                    "message": f"{tickers[0].upper()} not found.",
                    "disclaimer": DISCLAIMER_TEXT,
                },
                status_code=404,
            )
        dividend_yield = stock.get("dividend_yield", "N/A")
        div_str = f"{dividend_yield * 100:.2f}%" if isinstance(dividend_yield, (int, float)) else str(dividend_yield)
        message = (
            f"{stock['name']} ({stock['ticker']}) has a dividend yield of {div_str}.\n"
            f"Price: KES {stock.get('price', 'N/A'):.2f}"
        )
        return {
            "type": "stock_info",
            "data": stock,
            "message": message,
            "disclaimer": DISCLAIMER_TEXT,
        }

    # ── TOP_MOVERS: Show best/worst performing stocks ─────────────────────
    if intent == "top_movers":
        overview = await asyncio.to_thread(get_market_overview)
        top_gainers = overview["top_gainers"]
        top_losers = overview["top_losers"]

        gainers_text = "\n".join([
            f"{s['ticker']}: {s['name']} ({s.get('change_pct', 0)}% | {s.get('price', 'N/A')})"
            for s in top_gainers
        ])
        losers_text = "\n".join([
            f"{s['ticker']}: {s['name']} ({s.get('change_pct', 0)}% | {s.get('price', 'N/A')})"
            for s in top_losers
        ])

        message = f"Top Gainers:\n{gainers_text}\n\nTop Losers:\n{losers_text}"
        return {
            "type": "market_overview",
            "data": overview,
            "message": message,
            "disclaimer": DISCLAIMER_TEXT,
        }

    # ── STOCK_SUMMARY: Detailed summary of a stock ──────────────────────────
    if intent == "stock_summary":
        if not tickers:
            return {
                "type": "error",
                "data": {},
                "message": "Please mention a stock to summarize.",
                "disclaimer": DISCLAIMER_TEXT,
            }
        stock = await _get_cached_stock_data(tickers[0], include_history=True)
        if not stock:
            return JSONResponse(
                {
                    "type": "error",
                    "data": {},
                    "message": f"{tickers[0].upper()} not found.",
                    "disclaimer": DISCLAIMER_TEXT,
                },
                status_code=404,
            )

        summary_msg = (
            _build_trend_analysis_message(request.query, stock, timeframe)
            if any(re.search(p, lowered_query) for p in TREND_INTENT_PATTERNS)
            else _build_local_analysis_message(normalized_query, [stock])
        )
        return {
            "type": "stock_info",
            "data": stock,
            "message": summary_msg,
            "disclaimer": DISCLAIMER_TEXT,
        }

    # ── FUNDAMENTALS: Show P/E, earnings, financial metrics ──────────────────
    if intent == "fundamentals":
        if not tickers:
            return {
                "type": "error",
                "data": {},
                "message": "Please mention a stock to see fundamentals.",
                "disclaimer": DISCLAIMER_TEXT,
            }
        stocks = await asyncio.gather(
            *[_get_cached_stock_data(t, include_history=False) for t in tickers]
        )
        valid_stocks = [s for s in stocks if s]

        if not valid_stocks:
            return JSONResponse(
                {
                    "type": "error",
                    "data": {},
                    "message": "Unable to fetch stock fundamentals.",
                    "disclaimer": DISCLAIMER_TEXT,
                },
                status_code=404,
            )

        fundamental_msg = "Stock Fundamentals:\n"
        for stock in valid_stocks:
            pe = stock.get("pe_ratio", "N/A")
            dividend = stock.get("dividend_yield", "N/A")
            pe_str = f"{pe:.2f}" if isinstance(pe, (int, float)) else pe
            div_str = f"{dividend * 100:.2f}%" if isinstance(dividend, (int, float)) else dividend
            fundamental_msg += (
                f"{stock['ticker']}: P/E {pe_str} | Dividend {div_str}\n"
            )

        return {
            "type": "stock_info",
            "data": {"stocks": valid_stocks},
            "message": fundamental_msg,
            "disclaimer": DISCLAIMER_TEXT,
        }

    # ── NEWS: Show recent news about stocks/market ──────────────────────────
    if intent == "news":
        # Fetch news from NewsAPI + Pinecone, and price data in parallel if ticker specified
        async def fetch_news_and_price():
            # Fetch from both NewsAPI and Pinecone in parallel
            api_news_task = asyncio.to_thread(
                news_module.get_stock_news,
                entity if entity else "NSE",
                None,
                5
            ) if entity else asyncio.sleep(0)
            pinecone_task = _query_all_namespaces(f"news {request.query}")
            price_task = (
                _get_cached_stock_data(entity, include_history=True)
                if entity
                else asyncio.sleep(0)
            )

            results = await asyncio.gather(
                api_news_task,
                pinecone_task,
                price_task,
                return_exceptions=True,
            )

            api_news = results[0] if not isinstance(results[0], Exception) else []
            pinecone_matches = results[1] if not isinstance(results[1], Exception) else []
            price_data = results[2] if not isinstance(results[2], Exception) else None

            return api_news, pinecone_matches, price_data

        api_news, pinecone_matches, price_data = await fetch_news_and_price()

        # Combine news from both sources
        pinecone_context = "\n".join(m["text"] for m in pinecone_matches if m.get("text"))
        news_summary = news_module.format_news_for_analysis(entity or "NSE", api_news) if api_news else ""
        combined_context = f"{news_summary}\n\n{pinecone_context}" if news_summary else pinecone_context

        if not combined_context.strip():
            return {
                "type": "error",
                "data": {},
                "message": f"No recent news available for {entity or 'NSE'} at this time.",
                "disclaimer": DISCLAIMER_TEXT,
            }

        # If no AI provider, return formatted response
        if not _has_openai_key():
            return {
                "type": "ai_response",
                "data": {"intent": "news", "ticker": entity},
                "message": combined_context,
                "disclaimer": DISCLAIMER_TEXT,
            }

        # Use AI to analyze price movement given news context
        if entity and price_data:
            prompt = _build_price_news_analysis_prompt(
                request.query,
                entity,
                price_data,
                combined_context
            )
        else:
            prompt = f"Summarize this NSE market news:\n\n{combined_context}\n\nThis is not financial advice."

        metadata = {
            "type": "ai_response",
            "data": {"intent": "news", "ticker": entity},
            "message": "",
            "disclaimer": DISCLAIMER_TEXT,
        }
        return StreamingResponse(
            _stream_sse_response(metadata, prompt),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # ── LEARN_MODE: Educational content about investing ─────────────────────
    if intent == "learn_mode":
        if entity in BEGINNER_TOPICS:
            return _build_local_education_response(normalized_query)

        if not _has_openai_key():
            return _build_local_education_response(normalized_query)

        metadata = {
            "type": "educational",
            "data": {"topic": entity or "general investing"},
            "message": "",
            "disclaimer": DISCLAIMER_TEXT,
        }
        prompt = (
            f"Provide educational content about {entity or 'investing in the NSE'} "
            f"related to: {normalized_query}"
        )
        return StreamingResponse(
            _stream_sse_response(metadata, prompt),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # ── COMPARE: Compare 2-4 stocks ──────────────────────────────────────────
    if intent == "compare":
        if len(tickers) < 2:
            return {
                "type": "error",
                "data": {},
                "message": "Please mention at least two NSE counters to compare.",
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

        if not payload["retrieved_context"]:
            return {
                "type": "comparison",
                "data": {
                    "stocks": payload["stocks"],
                    "scorecard": payload["scorecard"],
                    "analysis": payload["analysis"]
                    + " Document analysis is currently unavailable.",
                },
                "message": payload["analysis"]
                + " Document analysis is currently unavailable.",
                "disclaimer": DISCLAIMER_TEXT,
            }

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
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # ── AI_ADVICE: Default to AI-powered analysis ────────────────────────────
    # This is the fallback for any other intent
    # Fetch stocks, Pinecone context, and news (if ticker available) in parallel
    async def fetch_ai_advice_data():
        stock_tasks = [_get_cached_stock_data(t, include_history=True) for t in tickers]
        news_task = (
            asyncio.to_thread(news_module.get_stock_news, tickers[0], None, 5)
            if tickers
            else asyncio.to_thread(news_module.get_market_news, 5)
        )
        stocks_task = (
            asyncio.gather(*stock_tasks)
            if stock_tasks
            else asyncio.to_thread(get_all_stock_data, False)
        )

        results = await asyncio.gather(
            stocks_task,
            _query_all_namespaces(request.query) if tickers else asyncio.sleep(0),
            news_task,
            return_exceptions=True,
        )

        stocks = results[0] if not isinstance(results[0], Exception) else []
        if stocks is None:
            stocks = []
        pinecone_matches = results[1] if not isinstance(results[1], Exception) else []
        if pinecone_matches is None:
            pinecone_matches = []
        news_articles = results[2] if not isinstance(results[2], Exception) else []
        if news_articles is None:
            news_articles = []

        return stocks, pinecone_matches, news_articles

    stocks, pinecone_matches, news_articles = await fetch_ai_advice_data()
    valid_stocks = [s for s in stocks if s]
    retrieved_context = "\n".join(
        m["text"] for m in pinecone_matches if m.get("text")
    )

    # Add news context to retrieved context
    news_context = ""
    if news_articles:
        news_label = tickers[0] if tickers else "NSE market"
        news_context = news_module.format_news_for_analysis(news_label, news_articles)
    if news_context:
        retrieved_context = f"{retrieved_context}\n\nRecent News:\n{news_context}" if retrieved_context else news_context

    stock_context = "\n".join(
        (
            f"{stock['ticker']} {stock['name']}: price {_format_currency(stock.get('price'))}, "
            f"P/E {_format_ratio(stock.get('pe_ratio'))}, "
            f"yield {_format_percent(stock.get('dividend_yield'))}, "
            f"change {stock.get('change_pct', 'N/A')}%, source {stock.get('source', 'fallback')}"
        )
        for stock in valid_stocks[:12]
    )
    if stock_context:
        retrieved_context = (
            f"Current NSE price/fundamental context:\n{stock_context}\n\n{retrieved_context}"
            if retrieved_context
            else f"Current NSE price/fundamental context:\n{stock_context}"
        )

    if not tickers:
        return {
            "type": "ai_response",
            "data": {
                "tickers": [],
                "stocks": _rank_market_stocks(valid_stocks),
                "title": "Screening Shortlist",
                "news_available": bool(news_context),
            },
            "message": _build_market_recommendation_message(
                request.query,
                valid_stocks,
                news_context,
            ),
            "disclaimer": DISCLAIMER_TEXT,
        }

    if not _has_openai_key():
        return {
            "type": "ai_response",
            "data": {"tickers": tickers},
            "message": (
                _build_local_analysis_message(request.query, valid_stocks)
                if tickers
                else _build_market_recommendation_message(
                    request.query,
                    valid_stocks,
                    news_context,
                )
            ),
            "disclaimer": DISCLAIMER_TEXT,
        }

    if not retrieved_context:
        return {
            "type": "ai_response",
            "data": {"tickers": tickers},
            "message": (
                (
                    _build_local_analysis_message(request.query, valid_stocks)
                    if tickers
                    else _build_market_recommendation_message(
                        request.query,
                        valid_stocks,
                        news_context,
                    )
                )
                + " Document analysis is currently unavailable."
            ),
            "disclaimer": DISCLAIMER_TEXT,
        }

    metadata = {
        "type": "ai_response",
        "data": {"tickers": tickers},
        "message": "",
        "disclaimer": DISCLAIMER_TEXT,
    }

    # Add instruction for news-based analysis
    analysis_instruction = ""
    if news_context:
        analysis_instruction = "\n\n[Note: This analysis incorporates recent news. Always remind user this is not financial advice.]"

    prompt = _build_analysis_prompt(request.query, retrieved_context) + analysis_instruction
    return StreamingResponse(
        _stream_sse_response(metadata, prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
