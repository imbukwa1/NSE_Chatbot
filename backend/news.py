"""
NewsAPI integration for NSE Chatbot
Fetches recent news about stocks and companies
"""

import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
load_dotenv(BASE_DIR / ".env.example")

# NewsAPI configuration
NEWSAPI_BASE_URL = "https://newsapi.org/v2"


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

# Map NSE tickers to company names for news queries
TICKER_TO_COMPANY = {
    "SCOM": "Safaricom",
    "EQTY": "Equity Bank",
    "KCB": "KCB Group",
    "KQ": "Kenya Airways",
    "KPLC": "Kenya Power",
    "BAT": "BAT Tobacco",
    "EABL": "East African Breweries",
    "COOP": "Cooperative Bank",
    "BAMB": "Bamburi",
    "BRIT": "Britam",
    "DTK": "Diamond Trust",
    "KNRE": "Kenya Re",
    "NCBA": "NCBA Group",
    "SCBK": "Standard Chartered Kenya",
    "ABSA": "ABSA Bank",
    "IMH": "I&M Group",
    "KPLC": "Kenya Power",
    "TOTL": "TotalEnergies Kenya",
    "NSE": "Nairobi Securities Exchange",
    "NMG": "Nation Media Group",
    "CFC": "Stanbic Holdings Kenya",
}


def get_stock_news(ticker: str, company_name: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """
    Fetch recent news about a stock from NewsAPI.

    Args:
        ticker: NSE ticker symbol (e.g., "SCOM")
        company_name: Full company name (optional, if not provided uses ticker mapping)
        limit: Maximum number of articles to return (default 5, max 100)

    Returns:
        List of news articles with structure:
        {
            "source": {"name": "..."},
            "title": "...",
            "description": "...",
            "url": "...",
            "publishedAt": "2024-04-15T10:30:00Z",
            "content": "..."
        }

    Example:
        news = get_stock_news("SCOM")
        news = get_stock_news("SCOM", "Safaricom Kenya")
    """
    newsapi_key = os.getenv("NEWSAPI_KEY")
    if not _is_configured_secret(newsapi_key):
        logger.warning("NEWSAPI_KEY not set. News retrieval unavailable.")
        return []

    # Use provided company name or look up from ticker
    search_query = company_name or TICKER_TO_COMPANY.get(ticker, ticker)

    # Add NSE context to search
    search_query = f"{search_query} NSE Kenya stock"

    try:
        params = {
            "q": search_query,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": newsapi_key,
            "pageSize": limit,
        }

        response = requests.get(
            f"{NEWSAPI_BASE_URL}/everything",
            params=params,
            timeout=5,
        )

        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
            return []

        articles = data.get("articles", [])
        logger.info(f"Retrieved {len(articles)} articles for {ticker}")

        return articles

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching news: {e}")
        return []


def format_news_for_analysis(ticker: str, articles: list[dict[str, Any]]) -> str:
    """
    Format news articles into a readable string for GPT analysis.

    Args:
        ticker: Stock ticker symbol
        articles: List of news articles from get_stock_news()

    Returns:
        Formatted string with article titles and descriptions
    """
    if not articles:
        return f"No recent news found for {ticker}."

    formatted = f"Recent news for {ticker}:\n\n"
    for i, article in enumerate(articles[:5], 1):
        title = article.get("title", "")
        description = article.get("description", "")
        published = article.get("publishedAt", "").split("T")[0]  # Get date only

        formatted += f"{i}. [{published}] {title}\n"
        if description:
            formatted += f"   {description[:150]}...\n"
        formatted += "\n"

    return formatted


def get_market_news(limit: int = 10) -> list[dict[str, Any]]:
    """
    Fetch general NSE/Kenya stock market news.

    Args:
        limit: Maximum number of articles to return

    Returns:
        List of market news articles
    """
    newsapi_key = os.getenv("NEWSAPI_KEY")
    if not _is_configured_secret(newsapi_key):
        logger.warning("NEWSAPI_KEY not set. News retrieval unavailable.")
        return []

    try:
        params = {
            "q": "NSE Kenya stock market",
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": newsapi_key,
            "pageSize": limit,
        }

        response = requests.get(
            f"{NEWSAPI_BASE_URL}/everything",
            params=params,
            timeout=5,
        )

        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
            return []

        articles = data.get("articles", [])
        logger.info(f"Retrieved {len(articles)} market news articles")

        return articles

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching market news: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching market news: {e}")
        return []


if __name__ == "__main__":
    # Test the news module
    logging.basicConfig(level=logging.INFO)

    # Test single stock news
    print("Testing Safaricom news...")
    news = get_stock_news("SCOM")
    if news:
        print(format_news_for_analysis("SCOM", news))
    else:
        print("No news found for SCOM")

    # Test market news
    print("\nTesting market news...")
    market_news = get_market_news(5)
    if market_news:
        print(f"Found {len(market_news)} market news articles")
        for article in market_news[:3]:
            print(f"- {article['title']}")
    else:
        print("No market news found")
