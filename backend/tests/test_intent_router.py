#!/usr/bin/env python3
"""
Test script for the Featherless-compatible intent router.
Demonstrates classification of various user queries.
"""

import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

import intent_router

# Test queries for each intent
TEST_QUERIES = {
    "price_lookup": [
        "What is the price of Safaricom?",
        "How much is KCB trading right now?",
        "Show me SCOM price",
    ],
    "top_movers": [
        "Which stocks have moved the most today?",
        "Show me top performers",
        "What are the best performing stocks?",
    ],
    "stock_summary": [
        "Tell me about KCB",
        "Give me a summary of Equity Bank",
        "What can you tell me about BAT?",
    ],
    "dividend_info": [
        "What's the dividend yield for SCOM?",
        "Show me dividend information",
        "Which stocks pay good dividends?",
    ],
    "ai_advice": [
        "Should I invest in EABL?",
        "What's your recommendation for pension savings?",
        "Which stock should I buy?",
    ],
    "fundamentals": [
        "What's the P/E ratio?",
        "Show me financial metrics for KCB",
        "Tell me about earnings and valuation",
    ],
    "news": [
        "Any news about KQ?",
        "What's happening in the NSE market?",
        "Latest market updates",
    ],
    "learn_mode": [
        "How does the stock market work?",
        "Explain dividend investing",
        "Teach me about NSE trading",
    ],
}


async def test_intent_classification():
    """Test intent classification with sample queries."""
    print("=" * 80)
    print("FEATHERLESS INTENT ROUTER - TEST SUITE")
    print("=" * 80)

    api_key = Path("../.env").exists()

    if not api_key:
        print("\n[!] WARNING: Featherless API key not configured (.env file not found)")
        print("   Testing with FALLBACK mode (regex-based classification)")
        print("   For full demonstration, add FEATHERLESS_API_KEY and FEATHERLESS_CHAT_MODEL to .env file\n")

    print(f"\n[*] Testing {len(TEST_QUERIES)} intent types...\n")

    total_tests = 0

    for expected_intent, queries in TEST_QUERIES.items():
        print(f"\n{'-' * 80}")
        print(f"INTENT: {expected_intent.upper()}")
        print(f"{'-' * 80}")

        for query in queries:
            total_tests += 1
            print(f"\nQuery: \"{query}\"")

            try:
                # Use sync version to avoid async complexity
                result = intent_router.sync_classify(query)

                intent = result.get("intent", "unknown")
                entity = str(result.get("entity") or "—")
                confidence = float(result.get("confidence", 0.0)) if result.get("confidence") is not None else 0.0
                timeframe = str(result.get("timeframe") or "—")

                # Show result
                match_mark = "[OK]" if intent == expected_intent else "[FAIL]"
                print(f"  {match_mark} Intent: {intent:<20} (confidence: {confidence:.0%})")
                print(f"    Entity: {entity:<20} Timeframe: {timeframe}")

                if intent != expected_intent:
                    print(f"    [Expected: {expected_intent}]")

            except Exception as e:
                print(f"  [ERROR] {e}")

    print(f"\n{'=' * 80}")
    print(f"[OK] Completed {total_tests} classification tests")
    print(f"{'=' * 80}\n")


async def test_intent_routing():
    """Test routing classified intents to handlers."""
    print("\n" + "=" * 80)
    print("INTENT ROUTING TEST")
    print("=" * 80)

    sample_query = "What is the price of Safaricom?"
    print(f"\nSample Query: \"{sample_query}\"")

    # Classify
    classification = intent_router.sync_classify(sample_query)
    print(f"\n1. Classification Result:")
    print(f"   Intent: {classification['intent']}")
    print(f"   Entity: {classification['entity']}")
    print(f"   Timeframe: {classification['timeframe']}")
    print(f"   Confidence: {classification['confidence']:.0%}")

    # Route
    print(f"\n2. Routing to Handler...")
    routing_result = await intent_router.route(classification)
    print(f"   Handler: {routing_result.get('handler')}")
    print(f"   Description: {routing_result.get('description')}")
    print(f"   Confidence: {routing_result.get('confidence'):.0%}")


async def test_classify_and_route():
    """Test full classification and routing pipeline."""
    print("\n" + "=" * 80)
    print("FULL PIPELINE TEST (classify + route)")
    print("=" * 80)

    test_queries = [
        "What's the price of KCB?",
        "Compare SCOM and EQTY",
        "Should I buy BAT?",
    ]

    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        result = await intent_router.classify_and_route(query)
        print(f"  -> Intent: {result.get('classification', {}).get('intent')}")
        print(f"  -> Handler: {result.get('handler')}")


if __name__ == "__main__":
    print("\n")

    # Run classification tests
    asyncio.run(test_intent_classification())

    # Run routing tests
    asyncio.run(test_intent_routing())

    # Run full pipeline tests
    asyncio.run(test_classify_and_route())

    print("\n[OK] All tests completed!\n")



