import re
from typing import Optional

from services.llm_service import DISCLAIMER, classify_query as llm_classify_query, generate_response
from services.pinecone_service import query_documents
from services.structured_data import get_stock_data, load_stock_data

DISCLAIMER_TEXT = "This is not financial advice."
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
ANALYSIS_INTENT_PATTERNS = (
    r"\bwhy\b",
    r"\brisk\b",
    r"\banalysis\b",
    r"\bexplain\b",
    r"\boutlook\b",
    r"\bperformance\b",
)
COMPARE_INTENT_PATTERNS = (r"\bcompare\b", r"\bversus\b", r"\bvs\b")


def _normalize_message(text: str) -> str:
    cleaned = text.strip()
    disclaimer_phrase = DISCLAIMER.lower()
    if disclaimer_phrase in cleaned.lower():
        cleaned = re.sub(
            rf"\n*\s*{re.escape(DISCLAIMER)}\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
    return cleaned


def _build_response(response_type: str, data=None, message: str = "") -> dict:
    return {
        "type": response_type,
        "data": data or {},
        "message": message,
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


def _build_symbol_lookup() -> dict[str, str]:
    data = load_stock_data()
    symbol_lookup = {}
    for ticker, details in data.items():
        symbol_lookup[ticker.upper()] = ticker.upper()
        symbol_lookup[details["name"].lower()] = ticker.upper()
        for alias in details.get("aliases", []):
            symbol_lookup[alias.lower()] = ticker.upper()
    return symbol_lookup


def extract_tickers(user_query: str) -> list[str]:
    lookup = _build_symbol_lookup()
    normalized_query = user_query.lower()
    matches = []

    for alias, ticker in lookup.items():
        match = re.search(rf"\b{re.escape(alias)}\b", normalized_query)
        if match:
            matches.append((match.start(), len(alias), ticker))

    matched_tickers = []
    for _, _, ticker in sorted(matches):
        if ticker not in matched_tickers:
            matched_tickers.append(ticker)

    return matched_tickers


def classify_query(user_query: str, tickers: Optional[list[str]] = None) -> dict[str, str]:
    lowered_query = user_query.lower()
    if any(re.search(pattern, lowered_query) for pattern in COMPARE_INTENT_PATTERNS):
        return {"type": "compare"}
    if any(re.search(pattern, lowered_query) for pattern in PRICE_INTENT_PATTERNS):
        if not any(re.search(pattern, lowered_query) for pattern in ANALYSIS_INTENT_PATTERNS):
            return {"type": "price"}

    classification = llm_classify_query(user_query)
    query_type = classification.get("type", "analysis")
    if query_type == "compare":
        return {"type": "compare"}
    if query_type == "price":
        return {"type": "price"}
    return {"type": "analysis"}


def _safe_query_documents(query: str) -> list[dict]:
    try:
        return query_documents(query)
    except Exception:
        return []


def _safe_generate_response(prompt: str) -> Optional[str]:
    try:
        return generate_response(prompt)
    except Exception:
        return None


def _build_rag_context(question: str, tickers: list[str]) -> str:
    search_query = question if not tickers else f"{' '.join(tickers)} {question}"
    matches = _safe_query_documents(search_query)
    if not matches:
        return ""

    context_lines = []
    for match in matches:
        source = match.get("source") or "Annual report"
        text = match.get("text", "").strip()
        if text:
            context_lines.append(f"[{source}] {text}")

    return "\n".join(context_lines)


def build_ai_prompt(user_query: str, tickers: Optional[list[str]] = None) -> str:
    tickers = tickers or []
    context = _build_rag_context(user_query, tickers)
    return f"""
Question: {user_query}

Retrieved context from NSE company documents:
{context or "No Pinecone context was available."}

Write a concise, professional response in an NSE-focused financial analyst tone.
Use the retrieved context where relevant.
If the context is limited, say that briefly and stay conservative.
Include trend, risk level, strengths, and weaknesses where possible.
Keep the answer to 2-4 sentences and include the disclaimer exactly once.
""".strip()


def handle_structured_query(user_query: str, ticker: str) -> dict:
    stock = get_stock_data(ticker, include_history=False)
    if not stock:
        return _build_response(
            "error",
            message=f"{ticker} was not found in the structured NSE dataset.",
        )

    data = {
        "ticker": ticker.upper(),
        "name": stock["name"],
        "price": stock["price"],
        "history": stock["history"],
        "pe_ratio": stock.get("pe_ratio"),
        "dividend_yield": stock.get("dividend_yield"),
        "source": stock.get("source", "fallback"),
    }
    message = (
        f"{stock['name']} is trading at KES {stock['price']:.2f} "
        f"({data['source']} data)."
    )
    return _build_response("stock_info", data=data, message=message)


def handle_supported_prices() -> dict:
    stocks = []
    for ticker in load_stock_data().keys():
        stock = get_stock_data(ticker, include_history=False)
        if stock:
            stocks.append(stock)

    price_lines = [
        f"{stock['name']} ({stock['ticker']}): KES {stock['price']:.2f} [{stock.get('source', 'fallback')}]"
        for stock in stocks
    ]
    return _build_response(
        "stock_list",
        data={"stocks": stocks},
        message="Current supported NSE prices:\n" + "\n".join(price_lines),
    )


def handle_ai_query(user_query: str, tickers: Optional[list[str]] = None) -> dict:
    tickers = tickers or []
    prompt = build_ai_prompt(user_query, tickers)
    llm_response = _safe_generate_response(prompt)
    message = llm_response or (
        "I could not generate a document-grounded explanation at the moment. "
        "Please confirm your OpenAI and Pinecone configuration."
    )

    return _build_response(
        "ai_response",
        data={"tickers": tickers},
        message=_normalize_message(message),
    )


def handle_comparison(ticker1: str, ticker2: str) -> dict:
    ticker1 = ticker1.upper()
    ticker2 = ticker2.upper()
    stock1 = get_stock_data(ticker1, include_history=True)
    stock2 = get_stock_data(ticker2, include_history=True)

    if not stock1 or not stock2:
        return _build_response(
            "error",
            message="One or both tickers were not found in the structured dataset.",
        )

    qualitative_matches = _safe_query_documents(
        f"Compare {stock1['name']} and {stock2['name']} on risk, performance and outlook"
    )
    qualitative_context = "\n".join(
        match["text"] for match in qualitative_matches if match.get("text")
    )

    prompt = f"""
You are preparing a balanced scorecard for two NSE-listed counters.

Stock A: {stock1['name']} ({ticker1})
- Price: KES {stock1['price']:.2f}
- P/E ratio: {_format_ratio(stock1.get('pe_ratio'))}
- Dividend yield: {_format_percent(stock1.get('dividend_yield'))}

Stock B: {stock2['name']} ({ticker2})
- Price: KES {stock2['price']:.2f}
- P/E ratio: {_format_ratio(stock2.get('pe_ratio'))}
- Dividend yield: {_format_percent(stock2.get('dividend_yield'))}

Qualitative document context:
{qualitative_context or "No additional Pinecone context was available."}

Write a concise, professional NSE-focused comparison.
Include strengths, weaknesses, and a final recommendation.
Also include the price trend and risk level for each counter where context allows.
Keep the answer short and practical, and include the disclaimer exactly once.
""".strip()

    ai_insight = _safe_generate_response(prompt) or (
        f"{stock1['name']} currently looks stronger on stability, while {stock2['name']} "
        f"appears more speculative based on the available market data."
    )

    data = {
        "stock1": {
            "ticker": ticker1,
            "name": stock1["name"],
            "price": stock1["price"],
            "history": stock1["history"],
            "pe_ratio": stock1.get("pe_ratio"),
            "dividend_yield": stock1.get("dividend_yield"),
            "source": stock1.get("source", "fallback"),
        },
        "stock2": {
            "ticker": ticker2,
            "name": stock2["name"],
            "price": stock2["price"],
            "history": stock2["history"],
            "pe_ratio": stock2.get("pe_ratio"),
            "dividend_yield": stock2.get("dividend_yield"),
            "source": stock2.get("source", "fallback"),
        },
        "stock1_history": stock1["history"],
        "stock2_history": stock2["history"],
        "analysis": _normalize_message(ai_insight),
    }
    return _build_response("comparison", data=data, message="Comparison completed.")


def compare_stocks(ticker1: str, ticker2: str) -> dict:
    return handle_comparison(ticker1, ticker2)


def route_query(user_query: str) -> dict:
    tickers = extract_tickers(user_query)
    query_type = classify_query(user_query, tickers)["type"]

    if query_type == "compare":
        if len(tickers) < 2:
            return _build_response(
                "error",
                message="Please mention two NSE counters to compare.",
            )
        return handle_comparison(tickers[0], tickers[1])

    if query_type == "price":
        if tickers:
            return handle_structured_query(user_query, tickers[0])
        return handle_supported_prices()

    return handle_ai_query(user_query, tickers)
