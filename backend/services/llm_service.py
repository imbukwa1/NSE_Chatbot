import os
import json
from collections.abc import Iterator
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled at runtime
    OpenAI = None


DEFAULT_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
DEFAULT_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "180"))
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.5"))
CLASSIFIER_MAX_TOKENS = int(os.getenv("OPENAI_CLASSIFIER_MAX_TOKENS", "24"))
DISCLAIMER = "Disclaimer: This is not financial advice."

_client: Optional["OpenAI"] = None


def get_openai_client() -> "OpenAI":
    global _client

    if OpenAI is None:
        raise RuntimeError(
            "The OpenAI SDK is not installed. Install it with `pip install openai`."
        )

    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing. Add it to your environment or .env file."
            )
        _client = OpenAI(api_key=api_key)

    return _client


def _build_input(prompt: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "You are NSE AI Advisor, a professional financial research assistant "
                "focused on Kenyan capital markets. Write concise, analytical responses "
                "in a clear Nairobi Securities Exchange context. Do not overstate certainty. "
                "If context is limited, say so plainly."
            ),
        },
        {"role": "user", "content": prompt},
    ]


def _extract_response_text(response) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text.strip()

    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text_value = getattr(content, "text", None)
            if text_value:
                return text_value.strip()

    return ""


def _ensure_disclaimer(text: str) -> str:
    cleaned = text.strip()
    if DISCLAIMER.lower() not in cleaned.lower():
        cleaned = f"{cleaned}\n\n{DISCLAIMER}".strip()
    return cleaned


def _keyword_classify(query: str) -> dict[str, str]:
    lowered_query = query.lower()
    if any(keyword in lowered_query for keyword in ("compare", "versus", " vs ")):
        return {"type": "compare"}
    if any(
        keyword in lowered_query
        for keyword in ("price", "prices", "trading", "worth", "share price")
    ):
        return {"type": "price"}
    return {"type": "analysis"}


def classify_query(query: str) -> dict[str, str]:
    """Classify routing with GPT, falling back to local rules if OpenAI is unavailable."""
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=DEFAULT_CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify an NSE chatbot query. Return only compact JSON "
                        'with one key: {"type":"price"|"compare"|"analysis"}. '
                        "Use price for current price, trading value, worth, dividend, "
                        "or P/E lookup. Use compare for comparing two or more counters. "
                        "Use analysis for why, risk, performance, outlook, or explanation."
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=CLASSIFIER_MAX_TOKENS,
        )
        text = response.choices[0].message.content.strip()
        parsed = json.loads(text)
        classification_type = parsed.get("type")
        if classification_type in {"price", "compare", "analysis"}:
            return {"type": classification_type}
    except Exception:
        pass

    return _keyword_classify(query)


def generate_response(prompt: str) -> str:
    client = get_openai_client()

    response = client.chat.completions.create(
        model=DEFAULT_CHAT_MODEL,
        messages=_build_input(prompt),
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
    )

    text = response.choices[0].message.content.strip()
    if not text:
        raise RuntimeError("OpenAI returned an empty response.")

    return _ensure_disclaimer(text)


def generate_stream_response(prompt: str) -> Iterator[str]:
    client = get_openai_client()
    accumulated = ""

    stream = client.chat.completions.create(
        model=DEFAULT_CHAT_MODEL,
        messages=_build_input(prompt),
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
        stream=True,
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            delta = chunk.choices[0].delta.content
            if delta:
                accumulated += delta
                yield delta

    if DISCLAIMER.lower() not in accumulated.lower():
        disclaimer_suffix = f"\n\n{DISCLAIMER}"
        yield disclaimer_suffix
