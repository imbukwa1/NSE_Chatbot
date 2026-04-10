from __future__ import annotations

from services.pinecone_service import upsert_documents


ANNUAL_REPORTS_NAMESPACE = "annual_reports"
MACRO_NAMESPACE = "macro"


COMPANY_SUMMARIES = {
    "SCOM": "Safaricom reports resilient service revenue supported by mobile data, M-Pesa, fixed broadband and enterprise services. Profitability is supported by scale and strong cash generation. Key risks include regulatory pressure, competition in mobile money, capex needs for network quality, and currency exposure in regional expansion. Dividends remain an important shareholder return feature.",
    "EQTY": "Equity Group Holdings benefits from regional banking diversification, a large customer base and digital channels. Revenue is driven by net interest income, fees and transaction volumes. Key risks include asset quality, credit costs, sovereign exposure, FX volatility and competition. Dividends depend on capital needs and earnings momentum.",
    "KCB": "KCB Group has a broad East African banking footprint with revenue from lending, transaction banking and treasury operations. Profit can be affected by provisions, interest-rate movements and regional macro conditions. Key risks include non-performing loans, regulatory capital requirements and integration execution. Dividend capacity depends on profitability and capital adequacy.",
    "EABL": "East African Breweries generates revenue from beer and spirits brands across East Africa. Profitability depends on pricing power, input costs, excise taxes and consumer demand. Debt and working-capital needs are important watch areas. Key risks include tax increases, FX costs, distribution disruption and pressure on discretionary consumer spending.",
    "COOP": "Co-operative Bank of Kenya benefits from a strong co-operative movement franchise and a stable retail and SME base. Revenue is driven by lending, fees and digital banking. Key risks include credit quality, margin compression and macro pressure on borrowers. Dividends are supported when earnings and capital remain healthy.",
    "BAT": "BAT Kenya is a mature consumer defensive counter with strong brands and historically high cash generation. Revenue and profit are influenced by excise taxes, regulation and volume trends. Key risks include anti-tobacco regulation, illicit trade and tax policy. Dividends are a major part of the investment case.",
    "BAMB": "Bamburi Cement revenue depends on cement demand, infrastructure activity and construction cycles. Profitability is sensitive to energy, logistics and clinker costs. Key risks include intense competition, price pressure and slower construction demand. Balance-sheet strength and efficiency improvements are important for recovery.",
    "BRIT": "Britam Holdings earns from insurance, asset management and investment income. Performance depends on underwriting discipline, claims experience, investment returns and interest rates. Key risks include market volatility, insurance claims, capital adequacy and competition. Dividend outlook depends on sustainable profitability.",
    "DTK": "Diamond Trust Bank Kenya is a banking counter with revenue from loans, fees and treasury activities. It benefits from a conservative banking franchise and regional exposure. Key risks include loan quality, margin pressure, FX and regulatory capital needs. Dividends depend on earnings resilience and capital allocation.",
    "KNRE": "Kenya Reinsurance Corporation earns from reinsurance premiums and investment income. Profitability depends on claims experience, underwriting discipline and market returns. Key risks include catastrophe claims, insurance-cycle pricing, investment volatility and regional exposure. Dividends depend on underwriting and capital strength.",
}


MACRO_SUMMARIES = [
    {
        "id": "macro-cbk-rates",
        "ticker": "MACRO",
        "year": "2026",
        "page": 0,
        "text": "CBK interest rates influence NSE valuations through discount rates, bank margins and investor appetite for equities versus Treasury bills and bonds. Higher rates can support bank income but may pressure loan growth and increase credit risk. Lower rates can improve equity risk appetite and reduce finance costs.",
        "text_preview": "CBK interest rates influence NSE valuations through discount rates...",
    },
    {
        "id": "macro-kes-usd",
        "ticker": "MACRO",
        "year": "2026",
        "page": 0,
        "text": "KES/USD movements affect NSE companies with imported inputs, foreign currency debt, dollar revenues or regional operations. A weaker shilling can raise costs for fuel, equipment and raw materials, while exporters and firms with dollar revenues may benefit. FX volatility is especially relevant for airlines, manufacturers and banks.",
        "text_preview": "KES/USD movements affect NSE companies with imported inputs...",
    },
    {
        "id": "macro-inflation",
        "ticker": "MACRO",
        "year": "2026",
        "page": 0,
        "text": "Inflation affects consumer purchasing power, operating costs and monetary policy. High inflation can pressure margins for consumer and manufacturing firms unless pricing power is strong. It can also influence interest-rate expectations and investor preference between equities and fixed income.",
        "text_preview": "Inflation affects consumer purchasing power, operating costs...",
    },
    {
        "id": "macro-market-cap",
        "ticker": "MACRO",
        "year": "2026",
        "page": 0,
        "text": "NSE market capitalisation reflects investor confidence, liquidity and valuation trends across listed counters. Concentration in large counters such as Safaricom and major banks can heavily influence index performance. Liquidity, foreign investor flows and macro stability are important drivers of market breadth.",
        "text_preview": "NSE market capitalisation reflects investor confidence...",
    },
]


def build_company_records() -> list[dict]:
    return [
        {
            "id": f"synthetic-{ticker}-2026",
            "ticker": ticker,
            "year": "2026",
            "page": 0,
            "text": text,
            "text_preview": text[:240],
        }
        for ticker, text in COMPANY_SUMMARIES.items()
    ]


def main() -> None:
    annual_result = upsert_documents(build_company_records(), namespace=ANNUAL_REPORTS_NAMESPACE)
    macro_result = upsert_documents(MACRO_SUMMARIES, namespace=MACRO_NAMESPACE)
    print({"annual_reports": annual_result, "macro": macro_result})


if __name__ == "__main__":
    main()
