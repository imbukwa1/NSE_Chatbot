import re
from datetime import datetime
from typing import Any

from services.market_cache import get_market_status
from services.structured_data import get_all_stock_data, get_stock_data

SECTOR_BY_TICKER = {
    "SCOM": "Telecommunications",
    "EQTY": "Banking",
    "KCB": "Banking",
    "COOP": "Banking",
    "DTK": "Banking",
    "ABSA": "Banking",
    "NCBA": "Banking",
    "SCBK": "Banking",
    "IMH": "Banking",
    "CFC": "Banking",
    "KQ": "Aviation",
    "KPLC": "Utilities",
    "EABL": "Consumer",
    "BAT": "Consumer",
    "BAMB": "Construction",
    "BRIT": "Insurance",
    "KNRE": "Insurance",
    "TOTL": "Energy",
    "KENO": "Energy",
    "KAPC": "Agriculture",
    "NSE": "Financial Services",
    "NMG": "Media",
}


def market_status(now: datetime | None = None) -> dict[str, Any]:
    return get_market_status(now)


def enrich_stock(stock: dict[str, Any]) -> dict[str, Any]:
    history = stock.get("history") or []
    prices = [item.get("price") for item in history if item.get("price") is not None]
    high_52w = max(prices) if prices else None
    low_52w = min(prices) if prices else None
    price = stock.get("price")
    high_low_note = "N/A"

    if price is not None and high_52w and low_52w and high_52w != low_52w:
        position = (price - low_52w) / (high_52w - low_52w)
        if position >= 0.8:
            high_low_note = "near 52-week high"
        elif position <= 0.2:
            high_low_note = "near 52-week low"
        else:
            high_low_note = "mid-range"

    return {
        **stock,
        "sector": SECTOR_BY_TICKER.get(stock.get("ticker"), "Other"),
        "high_52w": high_52w,
        "low_52w": low_52w,
        "high_low_note": high_low_note,
    }


def get_enriched_stocks(include_history: bool = True) -> list[dict[str, Any]]:
    return [enrich_stock(stock) for stock in get_all_stock_data(include_history)]


def get_market_overview() -> dict[str, Any]:
    stocks = get_enriched_stocks(include_history=True)
    priced = [stock for stock in stocks if stock.get("price") is not None]
    sorted_by_change = sorted(
        priced, key=lambda stock: stock.get("change_pct") or 0, reverse=True
    )
    sorted_by_volume = sorted(
        priced, key=lambda stock: stock.get("volume") or 0, reverse=True
    )
    total_turnover = sum(
        (stock.get("price") or 0) * (stock.get("volume") or 0) for stock in priced
    )
    total_volume = sum(stock.get("volume") or 0 for stock in priced)

    return {
        "status": market_status(),
        "indices": [
            {
                "name": "NASI",
                "value": None,
                "change_pct": None,
                "source": "not configured",
            },
            {
                "name": "NSE 20",
                "value": None,
                "change_pct": None,
                "source": "not configured",
            },
            {
                "name": "NSE 25",
                "value": None,
                "change_pct": None,
                "source": "not configured",
            },
        ],
        "summary": {
            "listed_counters": len(priced),
            "total_turnover": round(total_turnover, 2),
            "shares_traded": total_volume,
            "deals": None,
            "foreign_participation": None,
            "bond_market_summary": "Not configured yet",
        },
        "top_gainers": sorted_by_change[:5],
        "top_losers": list(reversed(sorted_by_change[-5:])),
        "most_active": sorted_by_volume[:5],
        "dividend_leaders": sorted(
            priced, key=lambda stock: stock.get("dividend_yield") or 0, reverse=True
        )[:5],
        "stocks": priced,
    }


def stocks_by_sector(sector: str) -> list[dict[str, Any]]:
    normalized = sector.lower()
    return [
        stock
        for stock in get_enriched_stocks(include_history=True)
        if normalized in stock.get("sector", "").lower()
    ]


def build_market_overview_message(overview: dict[str, Any]) -> str:
    status = overview["status"]
    summary = overview["summary"]
    top = overview["top_gainers"][:3]
    top_text = ", ".join(
        f"{stock['ticker']} ({stock.get('change_pct', 0)}%)" for stock in top
    )
    return (
        f"NSE is currently {status['label'].lower()} ({status['hours']}). "
        f"Tracked counters: {summary['listed_counters']}. "
        f"Estimated turnover from available counter data is KES {summary['total_turnover']:,.2f}; "
        f"shares traded {summary['shares_traded']:,}. "
        f"Top gainers include {top_text or 'N/A'}. "
        "Index values, deals, foreign participation, and bonds require a connected NSE/CBK data feed."
    )


def parse_portfolio(query: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"(?P<quantity>\d+(?:,\d{3})*)\s+(?P<ticker>[A-Za-z&.-]{2,12})(?:\s+at\s+(?P<cost>\d+(?:\.\d+)?))?",
        re.IGNORECASE,
    )
    holdings = []
    for match in pattern.finditer(query):
        quantity = int(match.group("quantity").replace(",", ""))
        ticker = match.group("ticker")
        stock = get_stock_data(ticker, include_history=False)
        if not stock:
            continue
        cost = float(match.group("cost")) if match.group("cost") else None
        current_value = quantity * (stock.get("price") or 0)
        gain_loss = current_value - (quantity * cost) if cost is not None else None
        holdings.append(
            {
                "ticker": stock["ticker"],
                "name": stock["name"],
                "quantity": quantity,
                "price": stock.get("price"),
                "cost": cost,
                "current_value": round(current_value, 2),
                "gain_loss": round(gain_loss, 2) if gain_loss is not None else None,
                "dividend_income_estimate": round(
                    current_value * (stock.get("dividend_yield") or 0), 2
                ),
                "sector": SECTOR_BY_TICKER.get(stock["ticker"], "Other"),
            }
        )
    return holdings


def build_portfolio_payload(query: str) -> dict[str, Any] | None:
    holdings = parse_portfolio(query)
    if not holdings:
        return None

    total_value = sum(item["current_value"] for item in holdings)
    total_dividend = sum(item["dividend_income_estimate"] for item in holdings)
    sector_values: dict[str, float] = {}
    for item in holdings:
        sector_values[item["sector"]] = sector_values.get(item["sector"], 0) + item[
            "current_value"
        ]

    concentration_warning = None
    if total_value:
        top_sector, top_value = max(sector_values.items(), key=lambda entry: entry[1])
        weight = top_value / total_value
        if weight >= 0.7:
            concentration_warning = (
                f"{weight:.0%} of this portfolio is in {top_sector}; consider diversifying."
            )

    return {
        "holdings": holdings,
        "summary": {
            "total_value": round(total_value, 2),
            "estimated_annual_dividends": round(total_dividend, 2),
            "concentration_warning": concentration_warning,
        },
    }
