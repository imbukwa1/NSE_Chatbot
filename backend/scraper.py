"""
NSE Live Data Scraper
Fetches real-time stock data from afx.kwayisi.org/nse/ using BeautifulSoup.
"""
import pandas as pd
import logging
from datetime import datetime
from typing import Any
import requests
from bs4 import BeautifulSoup
from io import StringIO
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

        tables = pd.read_html(StringIO(response.text))
        if not tables:
            logger.warning("No tables found on the NSE page.")
            return None
        # The last table contains the stock listings
        df = tables[-1]

        print(df.columns)
        print(df.dtypes)

        print(df.head())
        stocks_data = {}

        for _, row in df.iterrows():
            try:
                ticker = str(row["Ticker"]).strip().upper()
                name = str(row["Name"]).strip()

                volume = 0 if pd.isna(row["Volume"]) else int(float(row["Volume"])) 
                price = 0.0 if pd.isna(row["Price"]) else float(row["Price"])
                change = 0.0 if pd.isna(row["Change"]) else float(row["Change"])

                stocks_data[ticker] = {
                    "ticker": ticker,
                    "name": name,
                    "price": price,
                    "change_pct": change,
                    "volume": volume,
                    "source": "live_scrape",
                }
            except Exception as e:
                print(f"Skipping {row.to_dict()}")
                print(e)

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
if __name__ == "__main__":
    print("Testing scraper...")
    data = scrape_nse_data()
    print("\nReturned data:")
    print(data)

