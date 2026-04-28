"""
NSE Live Data Scraper
Fetches real-time stock data from afx.kwayisi.org/nse/ using BeautifulSoup.
"""

import logging
from datetime import datetime
from typing import Any
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def scrape_nse_data() -> dict[str, dict[str, Any]] | None:
    """
    Scrape live NSE data from afx.kwayisi.org/nse/

    Returns:
        Dictionary with stocks data: {ticker: {name, price, change, volume, ...}}
        None if scrape fails
    """
    try:
        url = "https://afx.kwayisi.org/nse/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Try multiple table selectors (website structure may vary)
        table = None
        selectors = [
            lambda s: s.find("table", {"class": "market-data"}),
            lambda s: s.find("table", {"class": "data-table"}),
            lambda s: s.find("table", {"class": "stocks-table"}),
            lambda s: s.find("table", {"class": "table"}),
            lambda s: s.find_all("table")[0] if s.find_all("table") else None,  # First table fallback
        ]

        for selector in selectors:
            try:
                table = selector(soup)
                if table:
                    logger.debug(f"Found table using selector: {selector}")
                    break
            except (IndexError, AttributeError):
                continue

        if not table:
            logger.warning("Could not find stocks table in response - website structure may have changed")
            logger.debug(f"Page response length: {len(response.content)} bytes")
            return None

        stocks_data = {}
        rows = table.find_all("tr")[1:]  # Skip header row

        if not rows:
            logger.warning("Table found but no data rows - structure may have changed")
            return None

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:  # Ensure minimum columns
                continue

            try:
                # Extract data from columns (structure may vary)
                ticker = cols[0].get_text(strip=True).upper()
                name = cols[1].get_text(strip=True)
                price_str = cols[2].get_text(strip=True).replace(",", "")
                change_str = cols[3].get_text(strip=True).replace("%", "").replace(",", "")
                volume_str = cols[4].get_text(strip=True).replace(",", "")

                # Clean and convert values
                if not ticker or not price_str:
                    continue

                price = float(price_str)
                change = float(change_str) if change_str else 0.0
                volume = int(float(volume_str)) if volume_str else 0

                stocks_data[ticker] = {
                    "ticker": ticker,
                    "name": name,
                    "price": price,
                    "change_pct": change,
                    "volume": volume,
                    "source": "live_scrape",
                }

            except (ValueError, IndexError, AttributeError) as e:
                logger.debug(f"Error parsing row {cols[0] if cols else '?'}: {e}")
                continue

        if stocks_data:
            logger.info(f"Successfully scraped {len(stocks_data)} stocks from afx.kwayisi.org/nse/")
            return stocks_data
        else:
            logger.warning("No stocks parsed from table - you may need to update CSS selectors")
            return None

    except requests.RequestException as e:
        logger.error(f"Request failed while scraping NSE data: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during scraping: {e}")
        return None


def get_last_scraped_time() -> str:
    """Return the current time in ISO format."""
    return datetime.now().isoformat()
