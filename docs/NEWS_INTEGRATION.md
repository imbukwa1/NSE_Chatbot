# News Integration for NSE Chatbot

## Overview

The NSE Chatbot now includes real-time news integration via [NewsAPI](https://newsapi.org), allowing the system to:
- Fetch current news about NSE-listed stocks
- Combine price movements with recent news context
- Provide AI-powered analysis linking price changes to market events
- Always include disclaimers that analysis is not financial advice

## Setup Guide

### 1. Get a NewsAPI Key

1. Visit [https://newsapi.org](https://newsapi.org)
2. Click "Get API Key" (free tier available with 100 requests/day)
3. Sign up with email and verify your account
4. Copy your API key from the dashboard

### 2. Configure Environment Variable

Add your NewsAPI key to your `.env` file:

```sh
# .env
NEWSAPI_KEY=your-newsapi-key-here
```

Or export it in your terminal:

```bash
export NEWSAPI_KEY=your-newsapi-key-here
```

### 3. Install Dependencies

The required package is already in `requirements.txt`:

```bash
# Already included:
# - requests==2.33.0 (for HTTP calls)
# - newsapi-python==0.1.7 (for news search)
```

If you need to install manually:

```bash
pip install newsapi-python requests
```

## Architecture

### New Module: `news.py`

Located at `backend/news.py`, provides:

```python
get_stock_news(ticker, company_name=None, limit=5)
  → Fetches recent news for NSE ticker
  → Returns list of news articles with metadata

get_market_news(limit=10)
  → Fetches general NSE/Kenya stock market news

format_news_for_analysis(ticker, articles)
  → Formats articles into readable summary for GPT
```

**Example Usage:**

```python
import news

# Fetch news for Safaricom
articles = news.get_stock_news("SCOM")
formatted = news.format_news_for_analysis("SCOM", articles)
print(formatted)
# Output:
# Recent news for SCOM:
#
# 1. [2024-04-15] Safaricom expands 5G coverage across Kenya
#    Safaricom has announced new 5G infrastructure investments...
#
# 2. [2024-04-14] Telecom sector faces new regulatory changes
#    Kenya's telecoms regulator proposes stricter guidelines...
```

### Updated Handlers in `main.py`

#### News Intent Handler (`if intent == "news"`)

**Workflow:**
1. Fetch news from NewsAPI + Pinecone in parallel
2. Fetch price data for the ticker (if specified)
3. Format news summary
4. If OpenAI available: Use GPT to analyze price movement given news
5. If OpenAI unavailable: Return formatted news

**Example Flow:**
```
User: "Any news about Safaricom?"
         ↓
Intent Classification: news (entity: "SCOM")
         ↓
Parallel Fetch:
  - NewsAPI: Get 5 recent SCOM articles
  - Pinecone: Query document database for "news"
  - Database: Get current SCOM price
         ↓
Format News Context:
  "Recent news for SCOM:
   1. [2024-04-15] 5G expansion...
   2. [2024-04-14] regulatory changes..."
         ↓
GPT Analysis (if API key configured):
  Prompt: "Analyze this price movement given news context:
   SCOM trading at 30.45 (Change: +2.3%)
   Recent News: [formatted summary]

   Always add: This is not financial advice."
         ↓
Response: Streamed AI analysis linking price+news
```

#### AI Advice Intent Handler (Default fallback)

**Enhanced with News Context:**
1. Fetch stocks, Pinecone context, AND news in parallel
2. Combine retrieved contexts with news articles
3. Add instruction to GPT: Include disclaimer about news-based analysis
4. Stream response

**Example Flow:**
```
User: "Should I invest in Equity Bank?"
         ↓
Intent Classification: ai_advice (entity: "EQTY")
         ↓
Parallel Fetch:
  - Stock Data: EQTY price, P/E, dividend yield
  - Pinecone: Relevant documents about EQTY
  - NewsAPI: 5 recent EQTY articles
         ↓
Combined Context:
  "Stock: EQTY
   Price: 45.30 (Change: -1.2%)
   P/E: 8.5, Dividend Yield: 4.2%

   Recent News:
   1. [2024-04-15] Equity Bank reports Q1 earnings growth...
   2. [2024-04-14] Banking sector faces rate policy review..."
         ↓
GPT Analysis with reminder about news analysis disclaimer
         ↓
Response: "Equity Bank shows strong fundamentals with Q1 growth
         reported in recent news. However, sector-wide rate policy
         review could impact dividend yields.

         ⚠️ This is not financial advice."
```

## New Helper Function

Added to `main.py`:

```python
def _build_price_news_analysis_prompt(
    user_query: str,
    ticker: str,
    price_data: dict | None,
    news_summary: str
) -> str:
```

Builds prompt that:
- Combines price movement with news context
- Uses current price, P/E, dividend yield
- Includes formatted news articles
- Ends with explicit disclaimer

## API Specifications

### NewsAPI Endpoint
- Base: `https://newsapi.org/v2/everything`
- Method: GET
- Parameters:
  - `q`: Search query (e.g., "Safaricom NSE Kenya stock")
  - `sortBy`: "publishedAt" (most recent first)
  - `language`: "en"
  - `pageSize`: 5 (articles per query)
  - `apiKey`: Your NewsAPI key

### Rate Limits (Free Tier)
- 100 requests per day
- ~3-4 requests per user query (if news + market context fetched)
- Approximately 25-30 concurrent users per day

### Free Tier Features
- Access to news from 30,000+ sources
- 100 requests/day
- 1 month of historical data
- No credit card required

## Graceful Degradation

### When NEWSAPI_KEY is not set:
- News functions return empty lists `[]`
- Handlers fall back to Pinecone context only
- No error messages shown to user
- Full functionality preserved without news

**Example:**
```python
if not NEWSAPI_KEY:
    logger.warning("NEWSAPI_KEY not set. News retrieval unavailable.")
    return []
```

### When NewsAPI fails (network error, rate limit):
- Exception caught and logged
- Returns empty articles list
- Fallback to Pinecone context automatically

```python
except requests.exceptions.RequestException as e:
    logger.error(f"Error fetching news for {ticker}: {e}")
    return []
```

## Ticker-to-Company Mapping

The `news.py` module includes aliases for NSE tickers:

```python
TICKER_TO_COMPANY = {
    "SCOM": "Safaricom",
    "EQTY": "Equity Bank",
    "KCB": "KCB Group",
    "KQ": "Kenya Airways",
    # ... 15 more NSE stocks
}
```

When calling `get_stock_news("SCOM")`:
- Looks up: "Safaricom"
- Constructs query: "Safaricom NSE Kenya stock"
- Searches NewsAPI for relevant articles

## Requirements Updates

Added to `requirements.txt`:
```
newsapi-python==0.1.7
```

`requests==2.33.0` was already included.

## Usage Examples

### 1. News Intent
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Any news about Safaricom?"}'

# Response: Streaming AI analysis of SCOM news
```

### 2. AI Advice with News Context
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Should I invest in KCB given recent market conditions?"}'

# Response: Investment advice incorporating recent KCB news
```

### 3. Market News
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is happening in the NSE market today?"}'

# Response: General market news + analysis
```

## Testing

### Manual Test
```python
python -c "
import news
articles = news.get_stock_news('SCOM')
print(f'Fetched {len(articles)} articles')
if articles:
    print(news.format_news_for_analysis('SCOM', articles))
"
```

### Test Without API Key
```bash
# Even without NEWSAPI_KEY, functions work gracefully:
unset NEWSAPI_KEY
python backend/news.py
# Output: "[WARNING] NEWSAPI_KEY not set"
```

## Logging

Debug news operations via logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Watch logs for:
# - "Retrieved X articles for SCOM"
# - "Error fetching news: ..."
# - "NEWSAPI_KEY not set"
```

## Future Enhancements

1. **Sentiment Analysis**: Use GPT to score news sentiment
2. **News Caching**: Cache articles for 1-2 hours to reduce API calls
3. **Multi-Source Aggregation**: Combine NewsAPI + Pinecone directly
4. **News Alerts**: Notify users of major news affecting their portfolio
5. **Paid Tier**: Handle premium NewsAPI features (6+ months history, custom sources)

## Troubleshooting

### Issue: "No recent news available"
- Check NEWSAPI_KEY is valid
- Verify API key has quota remaining
- Try with different ticker symbol

### Issue: Slow responses
- Each query uses ~2-4 API calls
- 5 concurrent users = 10-20 API calls/minute
- Monitor rate limits at newsapi.org dashboard

### Issue: "Invalid JSON from GPT"
- Check OpenAI API key
- Ensure model is gpt-4o-mini (in .env)
- Review GPT response in logs

## References

- **NewsAPI**: https://newsapi.org
- **Documentation**: https://newsapi.org/docs
- **Free Tier**: 100 requests/day (sufficient for 25-30 daily users)
- **Support**: support@newsapi.org

---

## Implementation Checklist

- [x] Create `news.py` with NewsAPI integration
- [x] Update `main.py` to import news module
- [x] Update news intent handler with parallel calls
- [x] Update ai_advice handler with news context
- [x] Add helper function `_build_price_news_analysis_prompt()`
- [x] Add NEWSAPI_KEY to `.env.example`
- [x] Add newsapi-python to requirements.txt
- [x] Test graceful degradation without API key
- [x] Add logging for news operations
- [ ] User adds NEWSAPI_KEY to .env and restarts backend
- [ ] Frontend updates (optional): Show news articles in UI
