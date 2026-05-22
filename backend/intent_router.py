"""
Featherless-compatible intent router for NSE AI Advisor.

Featherless exposes an OpenAI-compatible chat completions API, so this module
keeps the existing router shape while swapping provider configuration.
"""

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

_client = None

SUPPORTED_INTENTS = {
    "price_lookup": "Get current price of a specific stock",
    "compare": "Compare two or more listed companies",
    "top_movers": "Find top performing or worst performing stocks",
    "stock_summary": "Get comprehensive summary of a stock",
    "dividend_info": "Get dividend yield and payment information",
    "ai_advice": "Request investment advice or analysis",
    "fundamentals": "Get fundamental metrics",
    "news": "Get news or recent updates about stocks",
    "learn_mode": "Learn about stocks, markets, or investing concepts",
}

TICKER_ALIASES = {
    "safaricom": "SCOM",
    "equity": "EQTY",
    "equity bank": "EQTY",
    "equity group": "EQTY",
    "kcb": "KCB",
    "kcb group": "KCB",
    "kenya commercial": "KCB",
    "kenya airways": "KQ",
    "airways": "KQ",
    "eabl": "EABL",
    "east african breweries": "EABL",
    "bat": "BAT",
    "british american tobacco": "BAT",
    "coop": "COOP",
    "co-operative bank": "COOP",
    "cooperative bank": "COOP",
    "bamburi": "BAMB",
    "britam": "BRIT",
    "diamond trust": "DTK",
    "dtb": "DTK",
    "i&m": "IMH",
    "im": "IMH",
    "kakuzi": "KZCO",
    "kplc": "KPLC",
    "kenya power": "KPLC",
}

SYSTEM_PROMPT = """You classify Nairobi Securities Exchange chatbot queries.

Return only valid JSON:
{"intent":"price_lookup|compare|top_movers|stock_summary|dividend_info|ai_advice|fundamentals|news|learn_mode","entity":"SCOM|KCB|EQTY|GENERAL","timeframe":"intraday|short_term|long_term|unspecified"}

Use:
- price_lookup for current price or quote questions
- compare for comparing two or more counters
- top_movers for gainers, losers, or most active stocks
- stock_summary for company overview questions
- dividend_info for dividends or yields
- ai_advice for risk, should I buy/sell, outlook, or recommendation questions
- fundamentals for P/E, EPS, valuation, and financial metrics
- news for latest updates or announcements
- learn_mode for educational questions
"""


class Intent:
    def __init__(
        self,
        intent: str,
        entity: str,
        timeframe: str,
        confidence: float = 1.0,
        raw_response: dict | None = None,
    ):
        self.intent = intent
        self.entity = entity
        self.timeframe = timeframe
        self.confidence = confidence
        self.raw_response = raw_response

    def is_valid(self) -> bool:
        return self.intent in SUPPORTED_INTENTS

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "entity": self.entity,
            "timeframe": self.timeframe,
            "confidence": self.confidence,
        }

    def __repr__(self) -> str:
        return (
            f"Intent(intent='{self.intent}', entity='{self.entity}', "
            f"timeframe='{self.timeframe}', confidence={self.confidence:.2f})"
        )


def _is_configured_secret(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    if not normalized:
        return False
    placeholders = ("your_", "your-", "replace", "placeholder", "example", "api_key_here")
    return not any(token in normalized for token in placeholders)


def get_client():
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("FEATHERLESS_API_KEY")
    model = os.getenv("FEATHERLESS_CHAT_MODEL")
    if not _is_configured_secret(api_key) or not model:
        logger.debug("Featherless intent router not configured; using fallback classifier")
        return None

    _client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"),
    )
    return _client


def normalize_ticker(entity: str | None) -> str:
    if not entity or entity.upper() == "GENERAL":
        return "GENERAL"

    cleaned = entity.strip()
    if cleaned.isupper() and 2 <= len(cleaned) <= 5 and cleaned.isalpha():
        return cleaned

    lowered = cleaned.lower()
    for alias, ticker in TICKER_ALIASES.items():
        if alias in lowered:
            return ticker

    return cleaned.upper()


def _extract_ticker_from_message(message: str) -> str:
    tickers = re.findall(r"\b[A-Z]{2,5}\b", message)
    if tickers:
        return tickers[0]

    lowered = message.lower()
    for alias, ticker in TICKER_ALIASES.items():
        if alias in lowered:
            return ticker

    return "GENERAL"


def _fallback_classify(user_message: str) -> Intent:
    lowered = user_message.lower()
    if re.search(r"\b(explain|teach|learn)\b", lowered):
        return Intent("learn_mode", "GENERAL", "unspecified", 0.7)

    patterns = {
        "compare": [r"\bcompare\b", r"\bversus\b", r"\bvs\b"],
        "top_movers": [r"\btop\b", r"\bgainers?\b", r"\blosers?\b", r"\bmost active\b", r"\bmovers?\b", r"\bmoved\b", r"\bperformers?\b", r"\bperforming\b"],
        "price_lookup": [r"\bprice\b", r"\bhow much\b", r"\bquote\b", r"\btrading\b", r"\bshare price\b"],
        "dividend_info": [r"\bdividends?\b", r"\byield\b", r"\bpayout\b"],
        "fundamentals": [r"\bp/e\b", r"\bpe ratio\b", r"\beps\b", r"\bvaluation\b", r"\bfundamental\b", r"\bfinancial metrics?\b", r"\bearnings\b"],
        "news": [r"\bnews\b", r"\bupdate\b", r"\bupdates\b", r"\blatest\b", r"\brecent\b", r"\bannouncement\b", r"\bhappening\b"],
        "ai_advice": [r"\bshould i\b", r"\badvice\b", r"\brecommendation\b", r"\brecommend\b", r"\bbuy\b", r"\bsell\b", r"\brisk\b", r"\boutlook\b"],
        "learn_mode": [r"\bexplain\b", r"\blearn\b", r"\bteach\b", r"\bhow\b", r"\bwhat is\b"],
        "stock_summary": [r"\btell me\b", r"\babout\b", r"\bsummary\b", r"\boverview\b"],
    }

    for intent, intent_patterns in patterns.items():
        if any(re.search(pattern, lowered) for pattern in intent_patterns):
            return Intent(intent, _extract_ticker_from_message(user_message), "unspecified", 0.7)

    return Intent("learn_mode", "GENERAL", "unspecified", 0.5)


def classify(user_message: str) -> Intent:
    client = get_client()
    if client is None:
        return _fallback_classify(user_message)

    try:
        model = os.getenv("FEATHERLESS_CHAT_MODEL")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        response_text = response.choices[0].message.content.strip()
        result = json.loads(response_text)
        intent = str(result.get("intent", "learn_mode")).lower()
        if intent not in SUPPORTED_INTENTS:
            intent = "learn_mode"

        return Intent(
            intent=intent,
            entity=normalize_ticker(result.get("entity", "GENERAL")),
            timeframe=str(result.get("timeframe", "unspecified")).lower(),
            confidence=1.0,
            raw_response=result,
        )
    except Exception as exc:
        logger.warning("Featherless intent classification failed; using fallback: %s", exc)
        return _fallback_classify(user_message)


def sync_classify(user_message: str) -> dict[str, Any]:
    return classify(user_message).to_dict()


def handle_intent(intent_obj: Intent, user_message: str = "", db_handler=None) -> dict[str, Any]:
    action_map = {
        "price_lookup": "query_live_price",
        "compare": "compare_stocks",
        "top_movers": "query_top_movers",
        "stock_summary": "query_stock_summary",
        "dividend_info": "query_dividend_info",
        "ai_advice": "generate_ai_advice",
        "fundamentals": "query_fundamentals",
        "news": "query_news",
        "learn_mode": "generate_educational_content",
    }
    return {
        "classification": intent_obj.to_dict(),
        "intent": intent_obj.intent,
        "entity": intent_obj.entity,
        "timeframe": intent_obj.timeframe,
        "confidence": intent_obj.confidence,
        "handler": action_map.get(intent_obj.intent, "generate_educational_content"),
        "description": SUPPORTED_INTENTS.get(intent_obj.intent, "Route user query"),
        "action": action_map.get(intent_obj.intent, "generate_educational_content"),
        "response": f"Processing {intent_obj.intent.replace('_', ' ')}...",
    }


async def route(classification: dict[str, Any]) -> dict[str, Any]:
    intent_obj = Intent(
        intent=classification.get("intent", "learn_mode"),
        entity=classification.get("entity", "GENERAL"),
        timeframe=classification.get("timeframe", "unspecified"),
        confidence=classification.get("confidence", 0.5),
    )
    return handle_intent(intent_obj)


async def classify_and_route(user_message: str) -> dict[str, Any]:
    intent = classify(user_message)
    return handle_intent(intent, user_message)


def debug_classify(user_message: str) -> None:
    intent = classify(user_message)
    print(intent)
    print(json.dumps(handle_intent(intent, user_message), indent=2))
