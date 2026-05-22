import os
import json
import logging
from collections.abc import Iterator
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled at runtime
    OpenAI = None


logger = logging.getLogger(__name__)

FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
DEFAULT_CHAT_MODEL = os.getenv("FEATHERLESS_CHAT_MODEL", "")
DEFAULT_MAX_TOKENS = int(os.getenv("FEATHERLESS_MAX_TOKENS", os.getenv("OPENAI_MAX_TOKENS", "180")))
DEFAULT_TEMPERATURE = float(os.getenv("FEATHERLESS_TEMPERATURE", os.getenv("OPENAI_TEMPERATURE", "0.5")))
CLASSIFIER_MAX_TOKENS = int(os.getenv("FEATHERLESS_CLASSIFIER_MAX_TOKENS", os.getenv("OPENAI_CLASSIFIER_MAX_TOKENS", "24")))
DISCLAIMER = "Disclaimer: This is not financial advice."

_chat_client: Optional["OpenAI"] = None
_openai_client: Optional["OpenAI"] = None


def _is_configured_secret(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    if not normalized:
        return False
    placeholders = ("your_", "your-", "replace", "placeholder", "example", "api_key_here")
    return not any(token in normalized for token in placeholders)


def get_provider_settings() -> dict[str, str]:
    """Return the active OpenAI-compatible chat provider settings."""
    return {
        "provider": "featherless",
        "api_key": os.getenv("FEATHERLESS_API_KEY", ""),
        "base_url": os.getenv("FEATHERLESS_BASE_URL", FEATHERLESS_BASE_URL),
        "model": os.getenv("FEATHERLESS_CHAT_MODEL", DEFAULT_CHAT_MODEL),
    }


def has_chat_provider() -> bool:
    settings = get_provider_settings()
    return _is_configured_secret(settings["api_key"]) and bool(settings["model"].strip())


def reset_clients_for_tests() -> None:
    global _chat_client, _openai_client
    _chat_client = None
    _openai_client = None


def get_chat_client() -> "OpenAI":
    """Initialize the Featherless OpenAI-compatible chat client lazily."""
    global _chat_client

    if OpenAI is None:
        raise RuntimeError(
            "The OpenAI SDK is not installed. Install it with `pip install openai`."
        )

    if _chat_client is None:
        settings = get_provider_settings()
        if not _is_configured_secret(settings["api_key"]):
            raise RuntimeError(
                "FEATHERLESS_API_KEY is missing. Add it to your environment or .env file."
            )
        if not settings["model"].strip():
            raise RuntimeError(
                "FEATHERLESS_CHAT_MODEL is missing. Add a Featherless chat model to your environment."
            )
        _chat_client = OpenAI(
            api_key=settings["api_key"],
            base_url=settings["base_url"],
        )

    return _chat_client


def get_openai_client() -> "OpenAI":
    """
    Legacy OpenAI client for embeddings/Pinecone only.

    Chat completions use Featherless through get_chat_client().
    """
    global _openai_client

    if OpenAI is None:
        raise RuntimeError(
            "The OpenAI SDK is not installed. Install it with `pip install openai`."
        )

    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not _is_configured_secret(api_key):
            raise RuntimeError(
                "OPENAI_API_KEY is missing. It is only needed for optional embeddings/Pinecone features."
            )
        _openai_client = OpenAI(api_key=api_key)

    return _openai_client


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
    """Classify routing with Featherless, falling back to local rules if unavailable."""
    try:
        client = get_chat_client()
        settings = get_provider_settings()
        response = client.chat.completions.create(
            model=settings["model"],
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
    except Exception as exc:
        logger.warning("Featherless intent classification failed; using local rules: %s", exc)

    return _keyword_classify(query)


def generate_response(prompt: str) -> str:
    client = get_chat_client()
    settings = get_provider_settings()

    response = client.chat.completions.create(
        model=settings["model"],
        messages=_build_input(prompt),
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
    )

    text = response.choices[0].message.content.strip()
    if not text:
        raise RuntimeError("Featherless returned an empty response.")

    return _ensure_disclaimer(text)


def generate_stream_response(prompt: str) -> Iterator[str]:
    client = get_chat_client()
    settings = get_provider_settings()
    accumulated = ""

    stream = client.chat.completions.create(
        model=settings["model"],
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
