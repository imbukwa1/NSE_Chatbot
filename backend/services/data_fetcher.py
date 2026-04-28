import csv
import io
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


NSE_MARKET_STATISTICS_URL = "https://www.nse.co.ke/market-statistics/"
NSE_CACHE_TTL_SECONDS = 30 * 60
YFINANCE_CACHE_TTL_SECONDS = 60 * 60


TICKER_ALIASES = {
    "SAFARICOM": "SCOM",
    "SAFCOM": "SCOM",
    "SCOM": "SCOM",
    "KQ": "KQ",
    "KENYA AIRWAYS": "KQ",
    "EQUITY": "EQTY",
    "EQUITY GROUP": "EQTY",
    "EQUITY GROUP HOLDINGS": "EQTY",
    "EQUITY BANK": "EQTY",
    "EQTY": "EQTY",
    "KCB": "KCB",
    "KCB GROUP": "KCB",
    "KCB GROUP PLC": "KCB",
    "EABL": "EABL",
    "EAST AFRICAN BREWERIES": "EABL",
    "COOP": "COOP",
    "CO-OP": "COOP",
    "COOPERATIVE BANK": "COOP",
    "CO-OPERATIVE BANK": "COOP",
    "BAT": "BAT",
    "BATK": "BAT",
    "BAMBURI": "BAMB",
    "BAMB": "BAMB",
    "BRITAM": "BRIT",
    "BRIT": "BRIT",
    "DIAMOND TRUST": "DTK",
    "DTB": "DTK",
    "DTK": "DTK",
    "KENYA RE": "KNRE",
    "KENYA REINSURANCE": "KNRE",
    "KNRE": "KNRE",
    "ABSA": "ABSA",
    "ABSA BANK": "ABSA",
    "NCBA": "NCBA",
    "NCBA GROUP": "NCBA",
    "SCBK": "SCBK",
    "STANDARD CHARTERED": "SCBK",
    "IMH": "IMH",
    "I&M": "IMH",
    "I&M GROUP": "IMH",
    "KPLC": "KPLC",
    "KENYA POWER": "KPLC",
    "KENYA POWER AND LIGHTING": "KPLC",
    "KENO": "KENO",
    "KENOLKOBIL": "KENO",
    "TOTL": "TOTL",
    "TOTAL": "TOTL",
    "TOTALENERGIES": "TOTL",
    "KAPC": "KAPC",
    "NSE": "NSE",
    "NMG": "NMG",
    "NATION": "NMG",
    "NATION MEDIA": "NMG",
    "CFC": "CFC",
    "STANBIC": "CFC",
    "STANBIC HOLDINGS": "CFC",
}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    cleaned = re.sub(r"[,%+]", "", str(value)).strip()
    if not cleaned or cleaned in {"-", "—"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _safe_int(value: Any) -> int | None:
    number = _safe_float(value)
    return int(number) if number is not None else None


class NSEDataFetcher:
    def __init__(self, seed_path: str | Path | None = None) -> None:
        self.seed_path = Path(seed_path) if seed_path else Path(__file__).resolve().parents[1] / "data" / "nse_seed.json"
        self._nse_cache: tuple[float, dict[str, dict[str, Any]]] | None = None
        self._yf_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}

    def resolve_ticker(self, ticker: str) -> str:
        cleaned = re.sub(r"\s+", " ", ticker.upper().strip())
        return TICKER_ALIASES.get(cleaned, cleaned)

    def get_price(self, ticker: str) -> dict[str, Any] | None:
        """Return ticker price data from NSE scraper, seed data, then yfinance. Never raises."""
        resolved_ticker = self.resolve_ticker(ticker)
        for getter in (self._get_from_nse, self._get_from_seed, self._get_from_yfinance):
            try:
                payload = getter(resolved_ticker)
                if payload and payload.get("price") is not None:
                    return payload
            except Exception:
                continue
        return None

    def get_all_seed_tickers(self) -> list[str]:
        return list(self._load_seed_data().keys())

    def _get_from_nse(self, ticker: str) -> dict[str, Any] | None:
        data = self._get_nse_prices()
        payload = data.get(ticker)
        if payload:
            return {**payload, "ticker": ticker, "source": "nse_scraper"}
        return None

    def _get_nse_prices(self) -> dict[str, dict[str, Any]]:
        if self._nse_cache:
            cached_at, payload = self._nse_cache
            if time.time() - cached_at < NSE_CACHE_TTL_SECONDS:
                return payload

        payload = self._scrape_nse_prices()
        self._nse_cache = (time.time(), payload)
        return payload

    def _scrape_nse_prices(self) -> dict[str, dict[str, Any]]:
        response = requests.get(NSE_MARKET_STATISTICS_URL, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        data = self._parse_html_tables(soup)
        if data:
            return data

        for link in soup.find_all("a"):
            label = link.get_text(" ", strip=True).lower()
            href = link.get("href")
            if href and "daily equity price list" in label:
                downloaded = self._parse_download(urljoin(NSE_MARKET_STATISTICS_URL, href))
                if downloaded:
                    return downloaded
        return {}

    def _parse_html_tables(self, soup: BeautifulSoup) -> dict[str, dict[str, Any]]:
        parsed: dict[str, dict[str, Any]] = {}
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [cell.get_text(" ", strip=True).lower() for cell in rows[0].find_all(["th", "td"])]
            for row in rows[1:]:
                values = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
                record = self._row_to_record(headers, values)
                if record:
                    parsed[record["ticker"]] = record
        return parsed

    def _parse_download(self, url: str) -> dict[str, dict[str, Any]]:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        text = response.text
        rows = list(csv.reader(io.StringIO(text)))
        if not rows:
            return {}
        headers = [header.lower().strip() for header in rows[0]]
        parsed = {}
        for values in rows[1:]:
            record = self._row_to_record(headers, values)
            if record:
                parsed[record["ticker"]] = record
        return parsed

    def _row_to_record(self, headers: list[str], values: list[str]) -> dict[str, Any] | None:
        if len(values) < 2:
            return None
        row = {header: values[index] for index, header in enumerate(headers) if index < len(values)}
        ticker = self.resolve_ticker(
            row.get("code")
            or row.get("ticker")
            or row.get("symbol")
            or row.get("security")
            or row.get("counter")
            or values[0]
        )
        price = _safe_float(
            row.get("price")
            or row.get("last")
            or row.get("last price")
            or row.get("closing price")
            or row.get("close")
        )
        if not ticker or price is None:
            return None

        name = row.get("company") or row.get("name") or row.get("security") or ticker
        change_pct = _safe_float(row.get("% change") or row.get("change %") or row.get("change_pct") or row.get("%change"))
        volume = _safe_int(row.get("volume") or row.get("shares traded") or row.get("total shares traded"))
        return {
            "ticker": ticker,
            "name": name,
            "price": price,
            "change_pct": change_pct,
            "volume": volume,
        }

    def _load_seed_data(self) -> dict[str, dict[str, Any]]:
        with self.seed_path.open("r", encoding="utf-8") as seed_file:
            raw_data = json.load(seed_file)
        return {self.resolve_ticker(ticker): value for ticker, value in raw_data.items()}

    def _get_from_seed(self, ticker: str) -> dict[str, Any] | None:
        payload = self._load_seed_data().get(ticker)
        if not payload:
            return None
        return {
            "ticker": ticker,
            "name": payload.get("name", ticker),
            "price": payload.get("price"),
            "change_pct": payload.get("change_pct"),
            "volume": payload.get("volume"),
            "source": "seed_data",
        }

    def _get_from_yfinance(self, ticker: str) -> dict[str, Any] | None:
        if yf is None:
            return None
        cached = self._yf_cache.get(ticker)
        if cached and time.time() - cached[0] < YFINANCE_CACHE_TTL_SECONDS:
            return cached[1]
        try:
            yf_ticker = yf.Ticker(f"{ticker}.NR")
            history = yf_ticker.history(period="5d", interval="1d", auto_adjust=False)
            if history is None or history.empty:
                self._yf_cache[ticker] = (time.time(), None)
                return None
            latest_price = float(history["Close"].dropna().iloc[-1])
            payload = {
                "ticker": ticker,
                "name": ticker,
                "price": round(latest_price, 2),
                "change_pct": None,
                "volume": None,
                "source": "yfinance",
            }
            self._yf_cache[ticker] = (time.time(), payload)
            return payload
        except Exception:
            self._yf_cache[ticker] = (time.time(), None)
            return None
