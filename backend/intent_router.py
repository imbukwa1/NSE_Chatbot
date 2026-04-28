"""
OpenAI Intent Router for NSE Chatbot
Routes user messages to specific intents using GPT-4o-mini
Includes fuzzy entity resolution using Pinecone vector search
"""

import asyncio
import json
import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client (lazy loading)
_client = None

def _get_client():
    """Get or initialize OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. Intent classification will use fallback patterns.")
            return None
        _client = OpenAI(api_key=api_key)
    return _client


# Define supported intents
SUPPORTED_INTENTS = {
    "price_lookup": "User wants current price for specific stock(s)",
    "top_movers": "User asks about best/worst performing stocks",
    "stock_summary": "User wants detailed summary/overview of a stock",
    "dividend_info": "User asks about dividends or dividend yields",
    "ai_advice": "User seeks investment advice or recommendations",
    "fundamentals": "User wants P/E ratio, earnings, financial metrics",
    "news": "User wants recent news or updates about stocks/market",
    "learn_mode": "User wants to learn about investing, markets, or finance concepts",
}

# System prompt for GPT-4o-mini
SYSTEM_PROMPT = f"""You are an intelligent intent classifier for an NSE (Nairobi Securities Exchange) financial chatbot.

Your task is to classify user messages into one of these intents:
{json.dumps(SUPPORTED_INTENTS, indent=2)}

Always respond with ONLY a valid JSON object, no other text. Follow this exact format:
{{{{
  "intent": "<one of the supported intents>",
  "entity": "<ticker symbol or entity mentioned, e.g., 'SCOM' or null>",
  "timeframe": "<'current', 'short_term', 'long_term', 'historical' or null>"
}}}}

Rules:
1. Extract ticker symbols from context (e.g., "Safaricom" → "SCOM", "KQ" → "KQ")
2. If no specific timeframe mentioned, set to null
3. If multiple tickers, use the first/main one for entity field
4. Be strict with intent classification - only use the supported intents
5. For NSE stocks: SCOM (Safaricom), EQTY (Equity), KCB (KCB Group), KQ (Kenya Airways),
   KPLC (KPLC), BAT (BAT), EABL (EABL), COOP (Co-op), BAMB (Bamburi), BRIT (Britam),
   DTK (Diamond Trust), CFCI (Crown Paints), UCHM (UCG), SCBK (Stanbic), ABSA (ABSA),
   NSE (NSE-listed), CIC (CIC Insurance), KE (Kenya Re), OMB (OMB), SWVL (Swvl)

Examples:
- "What is the price of Safaricom?" → {{"intent": "price_lookup", "entity": "SCOM", "timeframe": "current"}}
- "Which stocks have moved the most today?" → {{"intent": "top_movers", "entity": null, "timeframe": "current"}}
- "Tell me about KCB" → {{"intent": "stock_summary", "entity": "KCB", "timeframe": null}}
- "What's the dividend yield?" → {{"intent": "dividend_info", "entity": null, "timeframe": null}}
- "Should I buy EABL?" → {{"intent": "ai_advice", "entity": "EABL", "timeframe": null}}
- "What's the P/E ratio?" → {{"intent": "fundamentals", "entity": null, "timeframe": null}}
- "Any news about KQ?" → {{"intent": "news", "entity": "KQ", "timeframe": "recent"}}
- "Explain NSE market rules" → {{"intent": "learn_mode", "entity": "NSE", "timeframe": null}}
"""


async def classify(user_message: str) -> dict[str, Any]:
    """
    Classify a user message into an intent using GPT-4o-mini.

    Args:
        user_message: The user's query

    Returns:
        Dictionary with keys:
        - intent: str (one of SUPPORTED_INTENTS keys)
        - entity: str | None (ticker symbol or entity)
        - timeframe: str | None (current, short_term, long_term, historical)
        - confidence: float (0.0-1.0)
        - raw_response: str (for debugging)
    """
    client = _get_client()
    if not client:
        logger.warning("OpenAI client not available, returning ai_advice fallback")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": "OpenAI API key not configured",
            "message": user_message,
        }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.2,
            max_tokens=200,
        )

        raw_response = response.choices[0].message.content.strip()
        logger.debug(f"GPT-4o-mini raw response: {raw_response}")

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {raw_response}")
            raise ValueError(f"Invalid JSON from GPT: {e}")

        intent = result.get("intent", "").lower()
        if intent not in SUPPORTED_INTENTS:
            logger.warning(f"Unsupported intent from GPT: {intent}")
            intent = "ai_advice"

        entity = result.get("entity")
        if entity:
            entity = entity.upper()

        timeframe = result.get("timeframe")
        if timeframe:
            timeframe = timeframe.lower()

        confidence = 0.95 if result.get("intent") in SUPPORTED_INTENTS else 0.7

        classification = {
            "intent": intent,
            "entity": entity,
            "timeframe": timeframe,
            "confidence": confidence,
            "raw_response": raw_response,
            "message": user_message,
        }

        logger.info(f"Classified: {intent} (entity={entity}, timeframe={timeframe})")
        return classification

    except Exception as e:
        logger.error(f"Error classifying message: {e}")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": str(e),
            "message": user_message,
        }


def sync_classify(user_message: str) -> dict[str, Any]:
    """
    Synchronous version of classify (for non-async contexts).

    Args:
        user_message: The user's query

    Returns:
        Classification dictionary
    """
    client = _get_client()
    if not client:
        logger.warning("OpenAI client not available, returning ai_advice fallback")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": "OpenAI API key not configured",
            "message": user_message,
        }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.2,
            max_tokens=200,
        )

        raw_response = response.choices[0].message.content.strip()
        logger.debug(f"GPT-4o-mini raw response: {raw_response}")

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {raw_response}")
            raise ValueError(f"Invalid JSON from GPT: {e}")

        intent = result.get("intent", "").lower()
        if intent not in SUPPORTED_INTENTS:
            logger.warning(f"Unsupported intent from GPT: {intent}")
            intent = "ai_advice"

        entity = result.get("entity")
        if entity:
            entity = entity.upper()

        timeframe = result.get("timeframe")
        if timeframe:
            timeframe = timeframe.lower()

        confidence = 0.95 if result.get("intent") in SUPPORTED_INTENTS else 0.7

        classification = {
            "intent": intent,
            "entity": entity,
            "timeframe": timeframe,
            "confidence": confidence,
            "raw_response": raw_response,
            "message": user_message,
        }

        logger.info(f"Classified: {intent} (entity={entity}, timeframe={timeframe})")
        return classification

    except Exception as e:
        logger.error(f"Error classifying message: {e}")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": str(e),
            "message": user_message,
        }


async def resolve_fuzzy_entity(
    entity: str | None, user_message: str
) -> str | None:
    """
    Resolve ambiguous/fuzzy entity names to specific ticker using vector search.

    Used when entity is not a clear ticker symbol (e.g., "that big bank").
    Queries Pinecone to find the best matching stock.

    Args:
        entity: Extracted entity (may be fuzzy name or company name)
        user_message: Original user message for additional context

    Returns:
        Matched ticker symbol, or original entity if no match found
    """
    # If entity is already a valid ticker (2-5 uppercase letters), return as-is
    if entity and 2 <= len(entity) <= 5 and entity.isupper() and entity.isalpha():
        return entity

    # Don't query if entity is generic or missing
    if not entity or entity == "GENERAL":
        return entity

    try:
        # Try vector search
        import embeddings as embeddings_module

        # Use combination of entity and message context for better matching
        search_query = f"{entity} {user_message}" if entity else user_message
        matches = await embeddings_module.query_stock_by_description(
            search_query,
            top_k=1,
            threshold=0.5
        )

        if matches:
            matched_ticker = matches[0]["ticker"]
            score = matches[0].get("similarity_score", 0)
            logger.info(f"Vector search resolved '{entity}' to {matched_ticker} (score: {score:.3f})")
            return matched_ticker
        else:
            logger.debug(f"Vector search found no matches for '{entity}'")
            return entity

    except Exception as e:
        logger.debug(f"Vector search failed, keeping original entity: {e}")
        return entity


# Intent handlers
async def handle_price_lookup(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle price lookup intent."""
    return {
        "handler": "price_lookup",
        "entity": entity,
        "timeframe": timeframe,
        "description": "Fetch current price(s) for stock(s)",
    }


async def handle_top_movers(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle top movers intent."""
    return {
        "handler": "top_movers",
        "entity": entity,
        "timeframe": timeframe,
        "description": "Find best/worst performing stocks today",
    }


async def handle_stock_summary(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle stock summary intent."""
    return {
        "handler": "stock_summary",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Provide detailed summary for {entity or 'mentioned stock'}",
    }


async def handle_dividend_info(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle dividend info intent."""
    return {
        "handler": "dividend_info",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Show dividend yield and dividend history for {entity or 'stock'}",
    }


async def handle_ai_advice(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle AI advice intent."""
    return {
        "handler": "ai_advice",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Provide investment advice for {entity or 'portfolio'}",
    }


async def handle_fundamentals(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle fundamentals intent."""
    return {
        "handler": "fundamentals",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Show P/E ratio, earnings, and financial metrics for {entity or 'stock'}",
    }


async def handle_news(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle news intent."""
    return {
        "handler": "news",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Fetch recent news and updates about {entity or 'market'}",
    }


async def handle_learn_mode(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle learn mode intent."""
    return {
        "handler": "learn_mode",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Educational content about {entity or 'investing and finance'}",
    }


# Map intents to handlers
INTENT_HANDLERS = {
    "price_lookup": handle_price_lookup,
    "top_movers": handle_top_movers,
    "stock_summary": handle_stock_summary,
    "dividend_info": handle_dividend_info,
    "ai_advice": handle_ai_advice,
    "fundamentals": handle_fundamentals,
    "news": handle_news,
    "learn_mode": handle_learn_mode,
}


async def route(classification: dict[str, Any]) -> dict[str, Any]:
    """
    Route a classified message to its handler.

    Includes fuzzy entity resolution using vector search.

    Args:
        classification: Output from classify() function

    Returns:
        Handler result with routing metadata
    """
    intent = classification.get("intent", "ai_advice")
    handler = INTENT_HANDLERS.get(intent)

    if not handler:
        logger.warning(f"No handler for intent: {intent}, using ai_advice")
        handler = INTENT_HANDLERS["ai_advice"]

    entity = classification.get("entity")
    user_message = classification.get("message", "")
    timeframe = classification.get("timeframe")

    # Resolve fuzzy entity names using vector search
    if entity:
        resolved_entity = await resolve_fuzzy_entity(entity, user_message)
        if resolved_entity != entity:
            logger.info(f"Resolved entity: {entity} -> {resolved_entity}")
            entity = resolved_entity

    result = await handler(entity, timeframe)
    result.update({
        "classification": classification,
        "confidence": classification.get("confidence", 0.0),
        "resolved_entity": entity,  # Include resolved entity in result
    })

    return result


async def classify_and_route(user_message: str) -> dict[str, Any]:
    """
    Classify a message and immediately route to appropriate handler.

    Args:
        user_message: The user's query

    Returns:
        Handler result with full routing information
    """
    classification = await classify(user_message)
    routing_result = await route(classification)
    return routing_result
"""
OpenAI Intent Router for NSE Chatbot
Routes user messages to specific intents using GPT-4o-mini
"""

import asyncio
import json
import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client (lazy loading)
_client = None

def _get_client():
    """Get or initialize OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. Intent classification will use fallback patterns.")
            return None
        _client = OpenAI(api_key=api_key)
    return _client


# Define supported intents
SUPPORTED_INTENTS = {
    "price_lookup": "User wants current price for specific stock(s)",
    "top_movers": "User asks about best/worst performing stocks",
    "stock_summary": "User wants detailed summary/overview of a stock",
    "dividend_info": "User asks about dividends or dividend yields",
    "ai_advice": "User seeks investment advice or recommendations",
    "fundamentals": "User wants P/E ratio, earnings, financial metrics",
    "news": "User wants recent news or updates about stocks/market",
    "learn_mode": "User wants to learn about investing, markets, or finance concepts",
}

# System prompt for GPT-4o-mini
SYSTEM_PROMPT = f"""You are an intelligent intent classifier for an NSE (Nairobi Securities Exchange) financial chatbot.

Your task is to classify user messages into one of these intents:
{json.dumps(SUPPORTED_INTENTS, indent=2)}

Always respond with ONLY a valid JSON object, no other text. Follow this exact format:
{{{{
  "intent": "<one of the supported intents>",
  "entity": "<ticker symbol or entity mentioned, e.g., 'SCOM' or null>",
  "timeframe": "<'current', 'short_term', 'long_term', 'historical' or null>"
}}}}

Rules:
1. Extract ticker symbols from context (e.g., "Safaricom" → "SCOM", "KQ" → "KQ")
2. If no specific timeframe mentioned, set to null
3. If multiple tickers, use the first/main one for entity field
4. Be strict with intent classification - only use the supported intents
5. For NSE stocks: SCOM (Safaricom), EQTY (Equity), KCB (KCB Group), KQ (Kenya Airways),
   KPLC (KPLC), BAT (BAT), EABL (EABL), COOP (Co-op), BAMB (Bamburi), BRIT (Britam),
   DTK (Diamond Trust), CFCI (Crown Paints), UCHM (UCG), SCBK (Stanbic), ABSA (ABSA),
   NSE (NSE-listed), CIC (CIC Insurance), KE (Kenya Re), OMB (OMB), SWVL (Swvl)

Examples:
- "What is the price of Safaricom?" → {{"intent": "price_lookup", "entity": "SCOM", "timeframe": "current"}}
- "Which stocks have moved the most today?" → {{"intent": "top_movers", "entity": null, "timeframe": "current"}}
- "Tell me about KCB" → {{"intent": "stock_summary", "entity": "KCB", "timeframe": null}}
- "What's the dividend yield?" → {{"intent": "dividend_info", "entity": null, "timeframe": null}}
- "Should I buy EABL?" → {{"intent": "ai_advice", "entity": "EABL", "timeframe": null}}
- "What's the P/E ratio?" → {{"intent": "fundamentals", "entity": null, "timeframe": null}}
- "Any news about KQ?" → {{"intent": "news", "entity": "KQ", "timeframe": "recent"}}
- "Explain NSE market rules" → {{"intent": "learn_mode", "entity": "NSE", "timeframe": null}}
"""


async def classify(user_message: str) -> dict[str, Any]:
    """
    Classify a user message into an intent using GPT-4o-mini.

    Args:
        user_message: The user's query

    Returns:
        Dictionary with keys:
        - intent: str (one of SUPPORTED_INTENTS keys)
        - entity: str | None (ticker symbol or entity)
        - timeframe: str | None (current, short_term, long_term, historical)
        - confidence: float (0.0-1.0)
        - raw_response: str (for debugging)
    """
    client = _get_client()
    if not client:
        logger.warning("OpenAI client not available, returning ai_advice fallback")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": "OpenAI API key not configured",
            "message": user_message,
        }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.2,
            max_tokens=200,
        )

        raw_response = response.choices[0].message.content.strip()
        logger.debug(f"GPT-4o-mini raw response: {raw_response}")

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {raw_response}")
            raise ValueError(f"Invalid JSON from GPT: {e}")

        intent = result.get("intent", "").lower()
        if intent not in SUPPORTED_INTENTS:
            logger.warning(f"Unsupported intent from GPT: {intent}")
            intent = "ai_advice"

        entity = result.get("entity")
        if entity:
            entity = entity.upper()

        timeframe = result.get("timeframe")
        if timeframe:
            timeframe = timeframe.lower()

        confidence = 0.95 if result.get("intent") in SUPPORTED_INTENTS else 0.7

        classification = {
            "intent": intent,
            "entity": entity,
            "timeframe": timeframe,
            "confidence": confidence,
            "raw_response": raw_response,
            "message": user_message,
        }

        logger.info(f"Classified: {intent} (entity={entity}, timeframe={timeframe})")
        return classification

    except Exception as e:
        logger.error(f"Error classifying message: {e}")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": str(e),
            "message": user_message,
        }


def sync_classify(user_message: str) -> dict[str, Any]:
    """
    Synchronous version of classify (for non-async contexts).

    Args:
        user_message: The user's query

    Returns:
        Classification dictionary
    """
    client = _get_client()
    if not client:
        logger.warning("OpenAI client not available, returning ai_advice fallback")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": "OpenAI API key not configured",
            "message": user_message,
        }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.2,
            max_tokens=200,
        )

        raw_response = response.choices[0].message.content.strip()
        logger.debug(f"GPT-4o-mini raw response: {raw_response}")

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {raw_response}")
            raise ValueError(f"Invalid JSON from GPT: {e}")

        intent = result.get("intent", "").lower()
        if intent not in SUPPORTED_INTENTS:
            logger.warning(f"Unsupported intent from GPT: {intent}")
            intent = "ai_advice"

        entity = result.get("entity")
        if entity:
            entity = entity.upper()

        timeframe = result.get("timeframe")
        if timeframe:
            timeframe = timeframe.lower()

        confidence = 0.95 if result.get("intent") in SUPPORTED_INTENTS else 0.7

        classification = {
            "intent": intent,
            "entity": entity,
            "timeframe": timeframe,
            "confidence": confidence,
            "raw_response": raw_response,
            "message": user_message,
        }

        logger.info(f"Classified: {intent} (entity={entity}, timeframe={timeframe})")
        return classification

    except Exception as e:
        logger.error(f"Error classifying message: {e}")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": str(e),
            "message": user_message,
        }


async def resolve_fuzzy_entity(
    entity: str | None, user_message: str
) -> str | None:
    """
    Resolve ambiguous/fuzzy entity names to specific ticker using vector search.

    Used when entity is not a clear ticker symbol (e.g., "that big bank").
    Queries Pinecone to find the best matching stock.

    Args:
        entity: Extracted entity (may be fuzzy name or company name)
        user_message: Original user message for additional context

    Returns:
        Matched ticker symbol, or original entity if no match found
    """
    # If entity is already a valid ticker (2-5 uppercase letters), return as-is
    if entity and 2 <= len(entity) <= 5 and entity.isupper() and entity.isalpha():
        return entity

    # Don't query if entity is generic or missing
    if not entity or entity == "GENERAL":
        return entity

    try:
        # Try vector search
        import embeddings as embeddings_module

        # Use combination of entity and message context for better matching
        search_query = f"{entity} {user_message}" if entity else user_message
        matches = await embeddings_module.query_stock_by_description(
            search_query,
            top_k=1,
            threshold=0.5
        )

        if matches:
            matched_ticker = matches[0]["ticker"]
            score = matches[0].get("similarity_score", 0)
            logger.info(f"Vector search resolved '{entity}' to {matched_ticker} (score: {score:.3f})")
            return matched_ticker
        else:
            logger.debug(f"Vector search found no matches for '{entity}'")
            return entity

    except Exception as e:
        logger.debug(f"Vector search failed, keeping original entity: {e}")
        return entity


# Intent handlers
async def handle_price_lookup(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle price lookup intent."""
    return {
        "handler": "price_lookup",
        "entity": entity,
        "timeframe": timeframe,
        "description": "Fetch current price(s) for stock(s)",
    }


async def handle_top_movers(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle top movers intent."""
    return {
        "handler": "top_movers",
        "entity": entity,
        "timeframe": timeframe,
        "description": "Find best/worst performing stocks today",
    }


async def handle_stock_summary(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle stock summary intent."""
    return {
        "handler": "stock_summary",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Provide detailed summary for {entity or 'mentioned stock'}",
    }


async def handle_dividend_info(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle dividend info intent."""
    return {
        "handler": "dividend_info",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Show dividend yield and dividend history for {entity or 'stock'}",
    }


async def handle_ai_advice(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle AI advice intent."""
    return {
        "handler": "ai_advice",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Provide investment advice for {entity or 'portfolio'}",
    }


async def handle_fundamentals(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle fundamentals intent."""
    return {
        "handler": "fundamentals",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Show P/E ratio, earnings, and financial metrics for {entity or 'stock'}",
    }


async def handle_news(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle news intent."""
    return {
        "handler": "news",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Fetch recent news and updates about {entity or 'market'}",
    }


async def handle_learn_mode(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle learn mode intent."""
    return {
        "handler": "learn_mode",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Educational content about {entity or 'investing and finance'}",
    }


# Map intents to handlers
INTENT_HANDLERS = {
    "price_lookup": handle_price_lookup,
    "top_movers": handle_top_movers,
    "stock_summary": handle_stock_summary,
    "dividend_info": handle_dividend_info,
    "ai_advice": handle_ai_advice,
    "fundamentals": handle_fundamentals,
    "news": handle_news,
    "learn_mode": handle_learn_mode,
}


async def route(classification: dict[str, Any]) -> dict[str, Any]:
    """
    Route a classified message to its handler.

    Args:
        classification: Output from classify() function

    Returns:
        Handler result with routing metadata
    """
    intent = classification.get("intent", "ai_advice")
    handler = INTENT_HANDLERS.get(intent)

    if not handler:
        logger.warning(f"No handler for intent: {intent}, using ai_advice")
        handler = INTENT_HANDLERS["ai_advice"]

    entity = classification.get("entity")
    timeframe = classification.get("timeframe")

    result = await handler(entity, timeframe)
    result.update({
        "classification": classification,
        "confidence": classification.get("confidence", 0.0),
    })

    return result


async def classify_and_route(user_message: str) -> dict[str, Any]:
    """
    Classify a message and immediately route to appropriate handler.

    Args:
        user_message: The user's query

    Returns:
        Handler result with full routing information
    """
    classification = await classify(user_message)
    routing_result = await route(classification)
    return routing_result
"""
OpenAI Intent Router for NSE Chatbot
Routes user messages to specific intents using GPT-4o-mini
"""

import json
import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client (only if key is available)
_client = None

def _get_client():
    """Get or initialize OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. Intent classification will use fallback patterns.")
            return None
        _client = OpenAI(api_key=api_key)
    return _client

# Define supported intents
SUPPORTED_INTENTS = {
    "price_lookup": "User wants current price for specific stock(s)",
    "top_movers": "User asks about best/worst performing stocks",
    "stock_summary": "User wants detailed summary/overview of a stock",
    "dividend_info": "User asks about dividends or dividend yields",
    "ai_advice": "User seeks investment advice or recommendations",
    "fundamentals": "User wants P/E ratio, earnings, financial metrics",
    "news": "User wants recent news or updates about stocks/market",
    "learn_mode": "User wants to learn about investing, markets, or finance concepts",
}

# System prompt for GPT-4o-mini
SYSTEM_PROMPT = f"""You are an intelligent intent classifier for an NSE (Nairobi Securities Exchange) financial chatbot.

Your task is to classify user messages into one of these intents:
{json.dumps(SUPPORTED_INTENTS, indent=2)}

Always respond with ONLY a valid JSON object, no other text. Follow this exact format:
{{{{
  "intent": "<one of the supported intents>",
  "entity": "<ticker symbol or entity mentioned, e.g., 'SCOM' or null>",
  "timeframe": "<'current', 'short_term', 'long_term', 'historical' or null>"
}}}}

Rules:
1. Extract ticker symbols from context (e.g., "Safaricom" → "SCOM", "KQ" → "KQ")
2. If no specific timeframe mentioned, set to null
3. If multiple tickers, use the first/main one for entity field
4. Be strict with intent classification - only use the supported intents
5. For NSE stocks: SCOM (Safaricom), EQTY (Equity), KCB (KCB Group), KQ (Kenya Airways),
   KPLC (KPLC), BAT (BAT), EABL (EABL), COOP (Co-op), BAMB (Bamburi), BRIT (Britam),
   DTK (Diamond Trust), CFCI (Crown Paints), UCHM (UCG), SCBK (Stanbic), ABSA (ABSA),
   NSE (NSE-listed), CIC (CIC Insurance), KE (Kenya Re), OMB (OMB), SWVL (Swvl)

Examples:
- "What is the price of Safaricom?" → {{"intent": "price_lookup", "entity": "SCOM", "timeframe": "current"}}
- "Which stocks have moved the most today?" → {{"intent": "top_movers", "entity": null, "timeframe": "current"}}
- "Tell me about KCB" → {{"intent": "stock_summary", "entity": "KCB", "timeframe": null}}
- "What's the dividend yield?" → {{"intent": "dividend_info", "entity": null, "timeframe": null}}
- "Should I buy EABL?" → {{"intent": "ai_advice", "entity": "EABL", "timeframe": null}}
- "What's the P/E ratio?" → {{"intent": "fundamentals", "entity": null, "timeframe": null}}
- "Any news about KQ?" → {{"intent": "news", "entity": "KQ", "timeframe": "recent"}}
- "Explain NSE market rules" → {{"intent": "learn_mode", "entity": "NSE", "timeframe": null}}
"""


async def classify(user_message: str) -> dict[str, Any]:
    """
    Classify a user message into an intent using GPT-4o-mini.

    Args:
        user_message: The user's query

    Returns:
        Dictionary with keys:
        - intent: str (one of SUPPORTED_INTENTS keys)
        - entity: str | None (ticker symbol or entity)
        - timeframe: str | None (current, short_term, long_term, historical)
        - confidence: float (0.0-1.0)
        - raw_response: str (for debugging)

    Raises:
        ValueError: If GPT returns invalid JSON or unsupported intent
    """
    client = _get_client()
    if not client:
        logger.warning("OpenAI client not available, returning ai_advice fallback")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": "OpenAI API key not configured",
            "message": user_message,
        }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.2,  # Lower temperature for consistent classification
            max_tokens=200,
        )

        # Extract the response text
        raw_response = response.choices[0].message.content.strip()
        logger.debug(f"GPT-4o-mini raw response: {raw_response}")

        # Parse JSON
        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {raw_response}")
            raise ValueError(f"Invalid JSON from GPT: {e}")

        # Validate intent
        intent = result.get("intent", "").lower()
        if intent not in SUPPORTED_INTENTS:
            logger.warning(f"Unsupported intent from GPT: {intent}")
            # Default to ai_advice if intent is unknown
            intent = "ai_advice"

        # Extract fields with defaults
        entity = result.get("entity")
        if entity:
            entity = entity.upper()  # Normalize ticker to uppercase

        timeframe = result.get("timeframe")
        if timeframe:
            timeframe = timeframe.lower()

        # Add confidence (based on response structure validity)
        confidence = 0.95 if result.get("intent") in SUPPORTED_INTENTS else 0.7

        classification = {
            "intent": intent,
            "entity": entity,
            "timeframe": timeframe,
            "confidence": confidence,
            "raw_response": raw_response,
            "message": user_message,
        }

        logger.info(f"Classified: {intent} (entity={entity}, timeframe={timeframe})")
        return classification

    except Exception as e:
        logger.error(f"Error classifying message: {e}")
        # Fallback to ai_advice on any error
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": str(e),
            "message": user_message,
        }


def sync_classify(user_message: str) -> dict[str, Any]:
    """
    Synchronous version of classify (for non-async contexts).

    Args:
        user_message: The user's query

    Returns:
        Classification dictionary (same as async version)
    """
    client = _get_client()
    if not client:
        logger.warning("OpenAI client not available, returning ai_advice fallback")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": "OpenAI API key not configured",
            "message": user_message,
        }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.2,
            max_tokens=200,
        )

        raw_response = response.choices[0].message.content.strip()
        logger.debug(f"GPT-4o-mini raw response: {raw_response}")

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {raw_response}")
            raise ValueError(f"Invalid JSON from GPT: {e}")

        intent = result.get("intent", "").lower()
        if intent not in SUPPORTED_INTENTS:
            logger.warning(f"Unsupported intent from GPT: {intent}")
            intent = "ai_advice"

        entity = result.get("entity")
        if entity:
            entity = entity.upper()

        timeframe = result.get("timeframe")
        if timeframe:
            timeframe = timeframe.lower()

        confidence = 0.95 if result.get("intent") in SUPPORTED_INTENTS else 0.7

        classification = {
            "intent": intent,
            "entity": entity,
            "timeframe": timeframe,
            "confidence": confidence,
            "raw_response": raw_response,
            "message": user_message,
        }

        logger.info(f"Classified: {intent} (entity={entity}, timeframe={timeframe})")
        return classification

    except Exception as e:
        logger.error(f"Error classifying message: {e}")
        return {
            "intent": "ai_advice",
            "entity": None,
            "timeframe": None,
            "confidence": 0.0,
            "raw_response": str(e),
            "message": user_message,
        }


# Intent handlers - These are called based on classification
async def handle_price_lookup(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle price lookup intent."""
    return {
        "handler": "price_lookup",
        "entity": entity,
        "timeframe": timeframe,
        "description": "Fetch current price(s) for stock(s)",
    }


async def handle_top_movers(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle top movers intent."""
    return {
        "handler": "top_movers",
        "entity": entity,
        "timeframe": timeframe,
        "description": "Find best/worst performing stocks today",
    }


async def handle_stock_summary(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle stock summary intent."""
    return {
        "handler": "stock_summary",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Provide detailed summary for {entity or 'mentioned stock'}",
    }


async def handle_dividend_info(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle dividend info intent."""
    return {
        "handler": "dividend_info",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Show dividend yield and dividend history for {entity or 'stock'}",
    }


async def handle_ai_advice(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle AI advice intent."""
    return {
        "handler": "ai_advice",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Provide investment advice for {entity or 'portfolio'}",
    }


async def handle_fundamentals(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle fundamentals intent."""
    return {
        "handler": "fundamentals",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Show P/E ratio, earnings, and financial metrics for {entity or 'stock'}",
    }


async def handle_news(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle news intent."""
    return {
        "handler": "news",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Fetch recent news and updates about {entity or 'market'}",
    }


async def handle_learn_mode(
    entity: str | None, timeframe: str | None
) -> dict[str, Any]:
    """Handle learn mode intent."""
    return {
        "handler": "learn_mode",
        "entity": entity,
        "timeframe": timeframe,
        "description": f"Educational content about {entity or 'investing and finance'}",
    }


# Map intents to handlers
INTENT_HANDLERS = {
    "price_lookup": handle_price_lookup,
    "top_movers": handle_top_movers,
    "stock_summary": handle_stock_summary,
    "dividend_info": handle_dividend_info,
    "ai_advice": handle_ai_advice,
    "fundamentals": handle_fundamentals,
    "news": handle_news,
    "learn_mode": handle_learn_mode,
}


async def route(classification: dict[str, Any]) -> dict[str, Any]:
    """
    Route a classified message to its handler.

    Args:
        classification: Output from classify() function

    Returns:
        Handler result with routing metadata
    """
    intent = classification.get("intent", "ai_advice")
    handler = INTENT_HANDLERS.get(intent)

    if not handler:
        logger.warning(f"No handler for intent: {intent}, using ai_advice")
        handler = INTENT_HANDLERS["ai_advice"]

    entity = classification.get("entity")
    timeframe = classification.get("timeframe")

    result = await handler(entity, timeframe)
    result.update({
        "classification": classification,
        "confidence": classification.get("confidence", 0.0),
    })

    return result


async def classify_and_route(user_message: str) -> dict[str, Any]:
    """
    Classify a message and immediately route to appropriate handler.

    Args:
        user_message: The user's query

    Returns:
        Handler result with full routing information
    """
    classification = await classify(user_message)
    routing_result = await route(classification)
    return routing_result
"""
Intent Router: Classify user queries using OpenAI gpt-4o-mini
Extracts: intent, entity (ticker), timeframe
"""

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client (lazy loading)
_client = None

def get_client():
    """Get or initialize OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set - intent classification will use fallback mode")
            return None
        _client = OpenAI(api_key=api_key)
    return _client

# Define supported intents
SUPPORTED_INTENTS = {
    "price_lookup": "Get current price of a specific stock",
    "top_movers": "Find top performing or worst performing stocks",
    "stock_summary": "Get comprehensive summary of a stock (price, P/E, dividend, etc.)",
    "dividend_info": "Get dividend yield and payment information",
    "ai_advice": "Request investment advice or analysis",
    "fundamentals": "Get fundamental metrics (P/E ratio, EPS, etc.)",
    "news": "Get news or recent updates about stocks",
    "learn_mode": "Learn about stocks, markets, or investing concepts",
}

SYSTEM_PROMPT = """You are an expert financial assistant classifier for the Nairobi Securities Exchange (NSE).

Your task is to classify user queries into one of these intents:
- price_lookup: User wants current price of a specific stock
- top_movers: User wants to know which stocks are gaining/losing
- stock_summary: User wants comprehensive info about a stock
- dividend_info: User asks about dividends or yields
- ai_advice: User asks for investment advice or "should I buy/sell"
- fundamentals: User asks about P/E, EPS, valuation metrics
- news: User asks for news or recent updates
- learn_mode: User wants to learn about markets/investing

Extract:
- intent: One of the above 8 intents
- entity: Stock ticker symbol (SCOM, EQTY, KCB, etc.) or "GENERAL" if not specific
- timeframe: "intraday", "short_term", "long_term", or "unspecified"

IMPORTANT: Respond ONLY with valid JSON, no other text.

Example 1:
User: "What's the price of Safaricom?"
Response: {"intent": "price_lookup", "entity": "SCOM", "timeframe": "intraday"}

Example 2:
User: "Which stocks went up today?"
Response: {"intent": "top_movers", "entity": "GENERAL", "timeframe": "intraday"}

Example 3:
User: "Tell me about Equity Bank's dividends"
Response: {"intent": "dividend_info", "entity": "EQTY", "timeframe": "unspecified"}

Example 4:
User: "Should I invest in KCB for the long term?"
Response: {"intent": "ai_advice", "entity": "KCB", "timeframe": "long_term"}

Example 5:
User: "Explain how stock markets work"
Response: {"intent": "learn_mode", "entity": "GENERAL", "timeframe": "unspecified"}

NSE Ticker Aliases (handle these):
- Safaricom: SCOM
- Equity Group/Bank: EQTY
- KCB Group: KCB
- Kenya Airways: KQ
- East African Breweries: EABL
- BAT: BAT
- Cooperative Bank: COOP
- Bamburi: BAMB
- Britam: BRIT
- Diamond Trust: DTK
- I&M Group: IMM
- Kakuzi: KZCO
- Kenya Commercial Bank: KCB
- Kenya Power: KPLC
- Compliant: COMPLIANT
- Car & General: CAG
"""

TICKER_ALIASES = {
    # Map common names to NSE ticker symbols
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
    "breweries": "EABL",
    "bat": "BAT",
    "british american tobacco": "BAT",
    "coop": "COOP",
    "cooperative bank": "COOP",
    "bamburi": "BAMB",
    "britam": "BRIT",
    "diamond trust": "DTK",
    "dtb": "DTK",
    "imm": "IMM",
    "i&m": "IMM",
    "kzco": "KZCO",
    "kakuzi": "KZCO",
    "kplc": "KPLC",
    "power": "KPLC",
    "kenya power": "KPLC",
    "compliant": "COMPLIANT",
    "cag": "CAG",
    "car and general": "CAG",
}


class Intent:
    """Represents a classified user intent."""

    def __init__(self,
                 intent: str,
                 entity: str,
                 timeframe: str,
                 confidence: float = 1.0,
                 raw_response: dict | None = None):
        self.intent = intent
        self.entity = entity
        self.timeframe = timeframe
        self.confidence = confidence
        self.raw_response = raw_response

    def is_valid(self) -> bool:
        """Check if intent is valid."""
        return self.intent in SUPPORTED_INTENTS

    def __repr__(self) -> str:
        return f"Intent(intent='{self.intent}', entity='{self.entity}', timeframe='{self.timeframe}', confidence={self.confidence:.2f})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intent": self.intent,
            "entity": self.entity,
            "timeframe": self.timeframe,
            "confidence": self.confidence,
        }


def normalize_ticker(entity: str) -> str:
    """
    Convert company name to ticker symbol.

    Examples:
        "Safaricom" → "SCOM"
        "Equity Bank" → "EQTY"
        "SCOM" → "SCOM" (already ticker)
    """
    if not entity or entity == "GENERAL":
        return "GENERAL"

    # Already a ticker (2-5 uppercase letters)
    if entity.isupper() and 2 <= len(entity) <= 5 and entity.isalpha():
        return entity

    # Look up in aliases
    lower_entity = entity.lower()
    for alias, ticker in TICKER_ALIASES.items():
        if alias in lower_entity or lower_entity == alias:
            return ticker

    # Return as-is if no match (might be a valid ticker)
    return entity.upper()


def classify(user_message: str) -> Intent:
    """
    Classify a user message into an intent using GPT-4o-mini.

    Args:
        user_message: The user's natural language query

    Returns:
        Intent object with intent, entity, timeframe
    """
    client = get_client()

    # If no API key, use fallback
    if client is None:
        logger.debug("Using fallback intent classification (no OpenAI API key)")
        return _fallback_classify(user_message)

    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.3,  # Deterministic
            max_tokens=200,
        )

        # Extract response text
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"GPT response: {response_text}")

        # Parse JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {response_text}")
            # Fallback to basic classification
            return _fallback_classify(user_message)

        # Validate and normalize
        intent = result.get("intent", "learn_mode").lower()
        entity = normalize_ticker(result.get("entity", "GENERAL"))
        timeframe = result.get("timeframe", "unspecified").lower()

        # Validate intent
        if intent not in SUPPORTED_INTENTS:
            logger.warning(f"Unknown intent '{intent}', defaulting to 'learn_mode'")
            intent = "learn_mode"

        return Intent(
            intent=intent,
            entity=entity,
            timeframe=timeframe,
            confidence=1.0,
            raw_response=result,
        )

    except Exception as e:
        logger.error(f"Error classifying intent: {e}")
        return _fallback_classify(user_message)


def _fallback_classify(user_message: str) -> Intent:
    """
    Fallback intent classification using regex patterns.
    Used when OpenAI API fails or returns invalid JSON.
    """
    msg_lower = user_message.lower()

    # Keywords for each intent
    patterns = {
        "price_lookup": [r"\bprice\b", r"\bhow much\b", r"\bquote\b", r"\b₿\.?\d+\b"],
        "top_movers": [r"\btop\b", r"\bgainers\b", r"\blosers\b", r"\bmovers\b", r"\bperforming\b"],
        "stock_summary": [r"\btell me\b", r"\babout\b", r"\bsummary\b", r"\boverview\b"],
        "dividend_info": [r"\bdividend\b", r"\byield\b", r"\bpayout\b"],
        "ai_advice": [r"\bshould i\b", r"\badvice\b", r"\brecommend\b", r"\bbuy\b", r"\bsell\b"],
        "fundamentals": [r"\bp/e\b", r"\bpe ratio\b", r"\beps\b", r"\bvaluation\b"],
        "news": [r"\bnews\b", r"\bupdate\b", r"\brecent\b", r"\bannouncement\b"],
        "learn_mode": [r"\bexplain\b", r"\blearn\b", r"\bhow\b", r"\bwhat is\b"],
    }

    # Find best matching intent
    for intent, keywords in patterns.items():
        for pattern in keywords:
            if re.search(pattern, msg_lower):
                # Try to extract ticker
                entity = _extract_ticker_from_message(user_message)
                return Intent(intent, entity, "unspecified", confidence=0.7)

    # Default to learn_mode
    return Intent("learn_mode", "GENERAL", "unspecified", confidence=0.5)


def _extract_ticker_from_message(message: str) -> str:
    """Extract ticker from message using regex and aliases."""
    # Look for uppercase 2-5 letter sequences
    tickers = re.findall(r"\b[A-Z]{2,5}\b", message)
    if tickers:
        return tickers[0]

    # Look for company names
    for alias, ticker in TICKER_ALIASES.items():
        if alias.lower() in message.lower():
            return ticker

    return "GENERAL"


# Handler functions for each intent
def handle_price_lookup(entity: str, db_handler=None) -> dict[str, Any]:
    """Handle price lookup intent."""
    return {
        "intent": "price_lookup",
        "entity": entity,
        "response": f"Fetching current price for {entity}...",
        "action": "query_live_price",
    }


def handle_top_movers(timeframe: str, db_handler=None) -> dict[str, Any]:
    """Handle top movers intent."""
    return {
        "intent": "top_movers",
        "timeframe": timeframe,
        "response": f"Analyzing top movers ({timeframe})...",
        "action": "query_top_movers",
    }


def handle_stock_summary(entity: str, db_handler=None) -> dict[str, Any]:
    """Handle stock summary intent."""
    return {
        "intent": "stock_summary",
        "entity": entity,
        "response": f"Generating comprehensive summary for {entity}...",
        "action": "query_stock_summary",
    }


def handle_dividend_info(entity: str, db_handler=None) -> dict[str, Any]:
    """Handle dividend info intent."""
    return {
        "intent": "dividend_info",
        "entity": entity,
        "response": f"Looking up dividend information for {entity}...",
        "action": "query_dividend_info",
    }


def handle_ai_advice(entity: str, context: str = "", db_handler=None) -> dict[str, Any]:
    """Handle AI advice intent."""
    return {
        "intent": "ai_advice",
        "entity": entity,
        "response": f"Analyzing {entity} for investment recommendation...",
        "action": "generate_ai_advice",
        "context": context,
    }


def handle_fundamentals(entity: str, db_handler=None) -> dict[str, Any]:
    """Handle fundamentals intent."""
    return {
        "intent": "fundamentals",
        "entity": entity,
        "response": f"Retrieving fundamental metrics for {entity}...",
        "action": "query_fundamentals",
    }


def handle_news(entity: str = "GENERAL", db_handler=None) -> dict[str, Any]:
    """Handle news intent."""
    return {
        "intent": "news",
        "entity": entity,
        "response": f"Searching for news about {entity}...",
        "action": "query_news",
    }


def handle_learn_mode(topic: str = "stocks", db_handler=None) -> dict[str, Any]:
    """Handle learn mode intent."""
    return {
        "intent": "learn_mode",
        "topic": topic,
        "response": f"Explaining {topic}...",
        "action": "generate_educational_content",
    }


# Intent dispatcher
INTENT_HANDLERS = {
    "price_lookup": handle_price_lookup,
    "top_movers": handle_top_movers,
    "stock_summary": handle_stock_summary,
    "dividend_info": handle_dividend_info,
    "ai_advice": handle_ai_advice,
    "fundamentals": handle_fundamentals,
    "news": handle_news,
    "learn_mode": handle_learn_mode,
}


def handle_intent(intent_obj: Intent, user_message: str = "", db_handler=None) -> dict[str, Any]:
    """
    Execute handler for classified intent.

    Args:
        intent_obj: Intent object from classify()
        user_message: Original user message (for context)
        db_handler: Optional database handler for queries

    Returns:
        Handler response with action and metadata
    """
    handler = INTENT_HANDLERS.get(intent_obj.intent, handle_learn_mode)

    try:
        if intent_obj.intent == "price_lookup":
            return handler(intent_obj.entity, db_handler)
        elif intent_obj.intent == "top_movers":
            return handler(intent_obj.timeframe, db_handler)
        elif intent_obj.intent == "ai_advice":
            return handler(intent_obj.entity, user_message, db_handler)
        elif intent_obj.intent == "news":
            return handler(intent_obj.entity, db_handler)
        elif intent_obj.intent == "learn_mode":
            # Extract topic from message or entity
            topic = intent_obj.entity if intent_obj.entity != "GENERAL" else "stocks"
            return handler(topic, db_handler)
        else:
            # Default: use entity as parameter
            return handler(intent_obj.entity, db_handler)

    except Exception as e:
        logger.error(f"Error handling intent: {e}")
        return {
            "intent": intent_obj.intent,
            "error": str(e),
            "response": "Sorry, I encountered an error processing your request.",
        }


def debug_classify(user_message: str) -> None:
    """Debug function to test intent classification."""
    print(f"\n{'='*70}")
    print(f"User Message: {user_message}")
    print(f"{'='*70}")

    intent = classify(user_message)
    print(f"Classification: {intent}")
    print(f"Is Valid: {intent.is_valid()}")
    print(f"To Dict: {intent.to_dict()}")

    handler_result = handle_intent(intent, user_message)
    print(f"Handler Result: {json.dumps(handler_result, indent=2)}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # Test classifications
    test_messages = [
        "What's the price of Safaricom?",
        "Which stocks went up today?",
        "Tell me about Equity Bank",
        "What dividend does KCB pay?",
        "Should I buy BAT for long-term investing?",
        "What's the P/E ratio of KPLC?",
        "Any news on NSE?",
        "Explain how stock markets work",
    ]

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    for msg in test_messages:
        debug_classify(msg)
