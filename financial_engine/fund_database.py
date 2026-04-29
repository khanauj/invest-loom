"""
fund_database.py - Static database of popular Indian mutual funds

~30 funds covering all categories with:
  name, fund_house, category, fund_type, risk,
  expense_ratio (%), returns_1yr/3yr/5yr (%), min_sip (INR)
"""

FUNDS = [
    # ── Large Cap ─────────────────────────────────────────────────────────────
    {
        "id": "uti_nifty50",
        "name": "UTI Nifty 50 Index Fund",
        "fund_house": "UTI",
        "category": "large_cap",
        "fund_type": "equity",
        "risk": "low_medium",
        "expense_ratio": 0.10,
        "returns_1yr": 12.5, "returns_3yr": 14.2, "returns_5yr": 13.8,
        "min_sip": 500,
        "best_for": "Passive large-cap core holding",
    },
    {
        "id": "icici_bluechip",
        "name": "ICICI Pru Bluechip Fund",
        "fund_house": "ICICI Prudential",
        "category": "large_cap",
        "fund_type": "equity",
        "risk": "low_medium",
        "expense_ratio": 1.65,
        "returns_1yr": 11.8, "returns_3yr": 13.5, "returns_5yr": 14.2,
        "min_sip": 100,
        "best_for": "Consistent active large-cap",
    },
    {
        "id": "mirae_large",
        "name": "Mirae Asset Large Cap Fund",
        "fund_house": "Mirae Asset",
        "category": "large_cap",
        "fund_type": "equity",
        "risk": "low_medium",
        "expense_ratio": 1.60,
        "returns_1yr": 12.1, "returns_3yr": 14.0, "returns_5yr": 15.1,
        "min_sip": 1000,
        "best_for": "Top active large-cap by 5yr returns",
    },

    # ── Mid Cap ───────────────────────────────────────────────────────────────
    {
        "id": "kotak_midcap",
        "name": "Kotak Emerging Equity Fund",
        "fund_house": "Kotak",
        "category": "mid_cap",
        "fund_type": "equity",
        "risk": "medium_high",
        "expense_ratio": 1.55,
        "returns_1yr": 18.2, "returns_3yr": 22.1, "returns_5yr": 20.8,
        "min_sip": 1000,
        "best_for": "High-quality mid-cap growth",
    },
    {
        "id": "axis_midcap",
        "name": "Axis Midcap Fund",
        "fund_house": "Axis",
        "category": "mid_cap",
        "fund_type": "equity",
        "risk": "medium_high",
        "expense_ratio": 1.72,
        "returns_1yr": 16.5, "returns_3yr": 19.8, "returns_5yr": 22.3,
        "min_sip": 500,
        "best_for": "Quality mid-cap, consistent alpha",
    },
    {
        "id": "nifty_midcap150",
        "name": "Motilal Oswal Nifty Midcap 150 Index Fund",
        "fund_house": "Motilal Oswal",
        "category": "mid_cap",
        "fund_type": "equity",
        "risk": "medium_high",
        "expense_ratio": 0.30,
        "returns_1yr": 17.0, "returns_3yr": 21.5, "returns_5yr": 19.2,
        "min_sip": 500,
        "best_for": "Low-cost passive mid-cap",
    },

    # ── Small Cap ─────────────────────────────────────────────────────────────
    {
        "id": "sbi_smallcap",
        "name": "SBI Small Cap Fund",
        "fund_house": "SBI",
        "category": "small_cap",
        "fund_type": "equity",
        "risk": "high",
        "expense_ratio": 1.76,
        "returns_1yr": 24.1, "returns_3yr": 28.5, "returns_5yr": 26.2,
        "min_sip": 500,
        "best_for": "Small-cap with strong track record",
    },
    {
        "id": "nippon_smallcap",
        "name": "Nippon India Small Cap Fund",
        "fund_house": "Nippon India",
        "category": "small_cap",
        "fund_type": "equity",
        "risk": "high",
        "expense_ratio": 1.66,
        "returns_1yr": 25.8, "returns_3yr": 30.2, "returns_5yr": 28.1,
        "min_sip": 100,
        "best_for": "Broadest small-cap portfolio in India",
    },

    # ── Flexi Cap ─────────────────────────────────────────────────────────────
    {
        "id": "parag_flexi",
        "name": "Parag Parikh Flexi Cap Fund",
        "fund_house": "PPFAS",
        "category": "flexi_cap",
        "fund_type": "equity",
        "risk": "medium",
        "expense_ratio": 1.32,
        "returns_1yr": 14.5, "returns_3yr": 18.2, "returns_5yr": 19.8,
        "min_sip": 1000,
        "best_for": "Value investing + international exposure (15%)",
    },
    {
        "id": "hdfc_flexi",
        "name": "HDFC Flexi Cap Fund",
        "fund_house": "HDFC",
        "category": "flexi_cap",
        "fund_type": "equity",
        "risk": "medium",
        "expense_ratio": 1.45,
        "returns_1yr": 16.2, "returns_3yr": 20.1, "returns_5yr": 17.8,
        "min_sip": 500,
        "best_for": "All-weather active flexi cap",
    },

    # ── ELSS (Tax Saving) ─────────────────────────────────────────────────────
    {
        "id": "mirae_elss",
        "name": "Mirae Asset Tax Saver Fund",
        "fund_house": "Mirae Asset",
        "category": "elss",
        "fund_type": "equity",
        "risk": "medium",
        "expense_ratio": 1.65,
        "returns_1yr": 12.8, "returns_3yr": 16.2, "returns_5yr": 20.1,
        "min_sip": 500,
        "best_for": "80C tax saving + best ELSS returns, 3yr lock-in",
    },
    {
        "id": "axis_elss",
        "name": "Axis Long Term Equity Fund (ELSS)",
        "fund_house": "Axis",
        "category": "elss",
        "fund_type": "equity",
        "risk": "medium",
        "expense_ratio": 1.61,
        "returns_1yr": 10.2, "returns_3yr": 14.5, "returns_5yr": 18.2,
        "min_sip": 500,
        "best_for": "80C tax saving with quality portfolio",
    },

    # ── International ─────────────────────────────────────────────────────────
    {
        "id": "motilal_nasdaq",
        "name": "Motilal Oswal Nasdaq 100 FOF",
        "fund_house": "Motilal Oswal",
        "category": "international",
        "fund_type": "equity",
        "risk": "medium_high",
        "expense_ratio": 0.58,
        "returns_1yr": 8.5, "returns_3yr": 15.2, "returns_5yr": 22.8,
        "min_sip": 500,
        "best_for": "US tech exposure, INR-USD hedge",
    },

    # ── Balanced Advantage / Hybrid ───────────────────────────────────────────
    {
        "id": "hdfc_baf",
        "name": "HDFC Balanced Advantage Fund",
        "fund_house": "HDFC",
        "category": "balanced_advantage",
        "fund_type": "hybrid",
        "risk": "medium",
        "expense_ratio": 1.58,
        "returns_1yr": 13.2, "returns_3yr": 16.8, "returns_5yr": 14.5,
        "min_sip": 500,
        "best_for": "Dynamic equity-debt allocation, lower volatility",
    },
    {
        "id": "icici_baf",
        "name": "ICICI Pru Balanced Advantage Fund",
        "fund_house": "ICICI Prudential",
        "category": "balanced_advantage",
        "fund_type": "hybrid",
        "risk": "medium",
        "expense_ratio": 1.55,
        "returns_1yr": 12.8, "returns_3yr": 15.2, "returns_5yr": 13.8,
        "min_sip": 1000,
        "best_for": "Conservative hybrid, smooths volatility",
    },
    {
        "id": "kotak_hybrid",
        "name": "Kotak Equity Hybrid Fund",
        "fund_house": "Kotak",
        "category": "aggressive_hybrid",
        "fund_type": "hybrid",
        "risk": "medium",
        "expense_ratio": 1.60,
        "returns_1yr": 14.5, "returns_3yr": 17.2, "returns_5yr": 15.8,
        "min_sip": 500,
        "best_for": "Aggressive hybrid ~65% equity, higher growth",
    },

    # ── Short Duration Debt ───────────────────────────────────────────────────
    {
        "id": "hdfc_shortdur",
        "name": "HDFC Short Duration Fund",
        "fund_house": "HDFC",
        "category": "short_duration",
        "fund_type": "debt",
        "risk": "low",
        "expense_ratio": 0.69,
        "returns_1yr": 7.2, "returns_3yr": 6.8, "returns_5yr": 7.1,
        "min_sip": 500,
        "best_for": "1-3 year parking, stable predictable returns",
    },
    {
        "id": "kotak_bond",
        "name": "Kotak Bond Short Term Fund",
        "fund_house": "Kotak",
        "category": "short_duration",
        "fund_type": "debt",
        "risk": "low",
        "expense_ratio": 0.85,
        "returns_1yr": 7.5, "returns_3yr": 7.2, "returns_5yr": 7.4,
        "min_sip": 1000,
        "best_for": "Conservative debt, 2-3 year horizon",
    },
    {
        "id": "sbi_gsec",
        "name": "SBI Gilt Fund",
        "fund_house": "SBI",
        "category": "gilt",
        "fund_type": "debt",
        "risk": "low_medium",
        "expense_ratio": 0.52,
        "returns_1yr": 8.1, "returns_3yr": 7.5, "returns_5yr": 8.0,
        "min_sip": 500,
        "best_for": "Government securities, zero credit risk",
    },

    # ── Liquid ────────────────────────────────────────────────────────────────
    {
        "id": "icici_liquid",
        "name": "ICICI Pru Liquid Fund",
        "fund_house": "ICICI Prudential",
        "category": "liquid",
        "fund_type": "debt",
        "risk": "very_low",
        "expense_ratio": 0.20,
        "returns_1yr": 6.8, "returns_3yr": 5.9, "returns_5yr": 5.8,
        "min_sip": 100,
        "best_for": "Emergency fund, ultra-safe overnight parking",
    },
    {
        "id": "axis_liquid",
        "name": "Axis Liquid Fund",
        "fund_house": "Axis",
        "category": "liquid",
        "fund_type": "debt",
        "risk": "very_low",
        "expense_ratio": 0.18,
        "returns_1yr": 6.9, "returns_3yr": 5.8, "returns_5yr": 5.9,
        "min_sip": 1000,
        "best_for": "Short-term parking up to 90 days",
    },

    # ── Gold ──────────────────────────────────────────────────────────────────
    {
        "id": "nippon_gold",
        "name": "Nippon India Gold ETF",
        "fund_house": "Nippon India",
        "category": "gold",
        "fund_type": "commodity",
        "risk": "medium",
        "expense_ratio": 0.82,
        "returns_1yr": 14.2, "returns_3yr": 11.5, "returns_5yr": 12.8,
        "min_sip": 500,
        "best_for": "Inflation hedge, portfolio diversifier",
    },
    {
        "id": "hdfc_gold",
        "name": "HDFC Gold ETF",
        "fund_house": "HDFC",
        "category": "gold",
        "fund_type": "commodity",
        "risk": "medium",
        "expense_ratio": 0.59,
        "returns_1yr": 14.0, "returns_3yr": 11.2, "returns_5yr": 12.5,
        "min_sip": 500,
        "best_for": "Lowest-cost gold ETF in India",
    },
]

# Category lookup map: alias -> list of category keys in FUNDS
CATEGORY_MAP = {
    "large_cap":          ["large_cap"],
    "mid_cap":            ["mid_cap"],
    "small_cap":          ["small_cap"],
    "flexi_cap":          ["flexi_cap"],
    "elss":               ["elss"],
    "international":      ["international"],
    "hybrid":             ["balanced_advantage", "aggressive_hybrid"],
    "balanced_advantage": ["balanced_advantage"],
    "aggressive_hybrid":  ["aggressive_hybrid"],
    "debt":               ["short_duration", "gilt"],
    "short_duration":     ["short_duration"],
    "gilt":               ["gilt"],
    "liquid":             ["liquid"],
    "gold":               ["gold"],
}


def get_fund_by_id(fund_id: str) -> dict:
    for f in FUNDS:
        if f["id"] == fund_id:
            return f
    return {}


def get_funds_by_category(category: str) -> list:
    keys = CATEGORY_MAP.get(category, [category])
    return [f for f in FUNDS if f["category"] in keys]


def search_funds(query: str) -> list:
    q = query.lower()
    return [f for f in FUNDS if q in f["name"].lower() or q in f["fund_house"].lower() or q in f["id"].lower()]


def get_all_funds() -> list:
    return FUNDS
