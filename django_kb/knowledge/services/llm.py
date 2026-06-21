import logging
import os
from dataclasses import dataclass


logger = logging.getLogger(__name__)

NSE_TERMS = {
    "nse", "share", "shares", "stock", "stocks", "dividend", "dividends", "market",
    "invest", "investment", "portfolio", "bond", "bonds", "trading", "broker", "cds",
    "safaricom", "equity", "kcb", "kenya", "valuation", "capital", "profit", "loss",
}


@dataclass(frozen=True)
class FallbackAnswer:
    answer: str
    source: str


def is_nse_focused(query):
    words = {word.strip(".,?!:;()[]\"").lower() for word in query.split()}
    return bool(words & NSE_TERMS)


def generate_nse_fallback(query):
    if not is_nse_focused(query):
        return FallbackAnswer(
            answer="I can only help with the Nairobi Securities Exchange, investing, and financial education questions.",
            source="guardrail",
        )

    api_key = os.getenv("FEATHERLESS_API_KEY", "").strip()
    model = os.getenv("FEATHERLESS_CHAT_MODEL", "").strip()
    if not api_key or not model:
        return FallbackAnswer(
            answer="I could not find a confident knowledge-base answer. Please rephrase the NSE question or mention a specific topic or company.",
            source="local_fallback",
        )

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"),
            timeout=20.0,
        )
        completion = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=350,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the NSE AI Advisor. Answer only questions about the Nairobi Securities Exchange, "
                        "Kenyan investing, or beginner financial education. Use simple English, distinguish facts "
                        "from general education, never invent live prices, and state when current data is unavailable."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )
        answer = (completion.choices[0].message.content or "").strip()
        if not answer:
            raise ValueError("The LLM returned an empty answer.")
        return FallbackAnswer(answer=answer, source="featherless")
    except Exception as exc:
        logger.warning("Featherless KB fallback failed: %s", exc)
        return FallbackAnswer(
            answer="The AI explanation service is temporarily unavailable. Please try again or ask a more specific NSE question.",
            source="local_fallback",
        )
