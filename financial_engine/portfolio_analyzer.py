"""
portfolio_analyzer.py - Itemized Portfolio Analysis Engine

Instead of just: equity_value = 200000
Now understands: HDFC Bank (Banking) + TCS (IT) + HDFC Index Fund

Features:
  - Sector mapping & concentration detection
  - Duplicate detection across stocks and mutual funds
  - Gap analysis (missing sectors/asset classes)
  - Smart derived features for ML compatibility
"""


# ──────────────────────────────────────────────
#  Stock Classification Knowledge Base
# ──────────────────────────────────────────────

# Market Cap Classification
STOCK_MARKET_CAP = {
    # Large Cap (Top 100 by market cap) — stable, low risk
    "Reliance": "large_cap", "TCS": "large_cap", "HDFC Bank": "large_cap",
    "ICICI Bank": "large_cap", "Infosys": "large_cap", "SBI": "large_cap",
    "HUL": "large_cap", "ITC": "large_cap", "Kotak Bank": "large_cap",
    "Airtel": "large_cap", "L&T": "large_cap", "Axis Bank": "large_cap",
    "Sun Pharma": "large_cap", "Bajaj Finance": "large_cap", "Maruti": "large_cap",
    "Tata Motors": "large_cap", "NTPC": "large_cap", "Nestle": "large_cap",
    "Wipro": "large_cap", "HCL Tech": "large_cap", "Power Grid": "large_cap",
    "Tata Steel": "large_cap", "ONGC": "large_cap", "BPCL": "large_cap",
    "Bajaj Finserv": "large_cap", "Adani Ports": "large_cap",
    "Tech Mahindra": "large_cap", "UltraTech": "large_cap",
    # Mid Cap (101-250) — growing, medium risk
    "IndusInd Bank": "mid_cap", "Bajaj Auto": "mid_cap",
    "Hero MotoCorp": "mid_cap", "Cipla": "mid_cap", "Britannia": "mid_cap",
    "Dr Reddy's": "mid_cap", "Divi's Labs": "mid_cap", "Dabur": "mid_cap",
    "Marico": "mid_cap", "M&M": "mid_cap", "Eicher Motors": "mid_cap",
    "HDFC Life": "mid_cap", "SBI Life": "mid_cap", "ICICI Lombard": "mid_cap",
    "ACC": "mid_cap", "LTIMindtree": "mid_cap", "Hindalco": "mid_cap",
    "JSW Steel": "mid_cap", "Apollo Hospitals": "mid_cap",
    "Godrej Properties": "mid_cap", "Adani Green": "mid_cap",
    # Small Cap (251+) — high risk, high return
    "DLF": "small_cap", "Jio": "small_cap",
}

# Growth vs Value Classification
STOCK_STYLE = {
    # Growth Stocks — fast growing, reinvest profits
    "TCS": "growth", "Infosys": "growth", "HCL Tech": "growth", "Wipro": "growth",
    "Bajaj Finance": "growth", "Adani Green": "growth", "Apollo Hospitals": "growth",
    "Divi's Labs": "growth", "LTIMindtree": "growth", "Tech Mahindra": "growth",
    # Value Stocks — undervalued, long-term potential
    "ITC": "value", "ONGC": "value", "BPCL": "value", "Tata Steel": "value",
    "SBI": "value", "NTPC": "value", "Power Grid": "value", "Hindalco": "value",
    "Coal India": "value", "JSW Steel": "value",
    # Blend (both growth + value characteristics)
    "HDFC Bank": "blend", "ICICI Bank": "blend", "Reliance": "blend",
    "HUL": "blend", "Maruti": "blend", "Sun Pharma": "blend",
}

# Dividend Classification
STOCK_DIVIDEND = {
    # Dividend Stocks — regular income, safe
    "ITC": True, "NTPC": True, "Power Grid": True, "ONGC": True,
    "BPCL": True, "Coal India": True, "HUL": True, "SBI": True,
    "Tata Steel": True, "Infosys": True, "TCS": True, "Wipro": True,
    "HDFC Bank": True, "ICICI Bank": True,
    # Non-Dividend — focus on growth
    "Bajaj Finance": False, "Adani Green": False, "DLF": False,
    "Apollo Hospitals": False, "Divi's Labs": False,
}

# Sector Classification
STOCK_SECTORS = {
    # Banking & Finance
    "HDFC Bank": "Banking", "ICICI Bank": "Banking", "SBI": "Banking",
    "Kotak Bank": "Banking", "Axis Bank": "Banking", "IndusInd Bank": "Banking",
    "Bajaj Finance": "Finance", "Bajaj Finserv": "Finance",
    "HDFC Life": "Insurance", "SBI Life": "Insurance", "ICICI Lombard": "Insurance",
    # IT
    "TCS": "IT", "Infosys": "IT", "Wipro": "IT", "HCL Tech": "IT",
    "Tech Mahindra": "IT", "LTIMindtree": "IT",
    # Pharma & Healthcare
    "Sun Pharma": "Pharma", "Dr Reddy's": "Pharma", "Cipla": "Pharma",
    "Divi's Labs": "Pharma", "Apollo Hospitals": "Healthcare",
    # FMCG
    "HUL": "FMCG", "ITC": "FMCG", "Nestle": "FMCG",
    "Britannia": "FMCG", "Dabur": "FMCG", "Marico": "FMCG",
    # Auto
    "Maruti": "Auto", "Tata Motors": "Auto", "M&M": "Auto",
    "Bajaj Auto": "Auto", "Hero MotoCorp": "Auto", "Eicher Motors": "Auto",
    # Energy & Oil
    "Reliance": "Conglomerate", "ONGC": "Oil & Gas", "BPCL": "Oil & Gas",
    "NTPC": "Power", "Power Grid": "Power", "Adani Green": "Power",
    # Metals & Mining
    "Tata Steel": "Metals", "Hindalco": "Metals", "JSW Steel": "Metals",
    # Telecom
    "Airtel": "Telecom", "Jio": "Telecom",
    # Cement & Infra
    "UltraTech": "Cement", "ACC": "Cement",
    "L&T": "Infrastructure", "Adani Ports": "Infrastructure",
    # Real Estate
    "DLF": "Real Estate", "Godrej Properties": "Real Estate",
}

MF_CATEGORIES = {
    # Large Cap
    "HDFC Index Fund": {"category": "Large Cap Index", "type": "equity", "sectors": ["Diversified"]},
    "UTI Nifty 50 Index Fund": {"category": "Large Cap Index", "type": "equity", "sectors": ["Diversified"]},
    "Nippon India Index Nifty": {"category": "Large Cap Index", "type": "equity", "sectors": ["Diversified"]},
    "Mirae Asset Large Cap": {"category": "Large Cap", "type": "equity", "sectors": ["Diversified"]},
    "Axis Bluechip Fund": {"category": "Large Cap", "type": "equity", "sectors": ["Diversified"]},
    "HDFC Top 100": {"category": "Large Cap", "type": "equity", "sectors": ["Diversified"]},
    # Mid Cap
    "Kotak Emerging Equity": {"category": "Mid Cap", "type": "equity", "sectors": ["Diversified"]},
    "Axis Midcap Fund": {"category": "Mid Cap", "type": "equity", "sectors": ["Diversified"]},
    "DSP Midcap Fund": {"category": "Mid Cap", "type": "equity", "sectors": ["Diversified"]},
    # Small Cap
    "SBI Small Cap Fund": {"category": "Small Cap", "type": "equity", "sectors": ["Diversified"]},
    "Nippon India Small Cap": {"category": "Small Cap", "type": "equity", "sectors": ["Diversified"]},
    "Axis Small Cap Fund": {"category": "Small Cap", "type": "equity", "sectors": ["Diversified"]},
    # Flexi / Multi Cap
    "Parag Parikh Flexi Cap": {"category": "Flexi Cap", "type": "equity", "sectors": ["Diversified", "International"]},
    "HDFC Flexi Cap": {"category": "Flexi Cap", "type": "equity", "sectors": ["Diversified"]},
    "Kotak Flexicap": {"category": "Flexi Cap", "type": "equity", "sectors": ["Diversified"]},
    # International
    "Motilal Oswal Nasdaq 100": {"category": "International", "type": "equity", "sectors": ["International"]},
    # Sectoral
    "ICICI Pru Technology Fund": {"category": "Sectoral", "type": "equity", "sectors": ["IT"]},
    "Nippon India Pharma Fund": {"category": "Sectoral", "type": "equity", "sectors": ["Pharma"]},
    "SBI Banking Fund": {"category": "Sectoral", "type": "equity", "sectors": ["Banking"]},
    # Hybrid
    "ICICI Pru BAF": {"category": "Balanced Advantage", "type": "hybrid", "sectors": ["Diversified"]},
    "HDFC BAF": {"category": "Balanced Advantage", "type": "hybrid", "sectors": ["Diversified"]},
    # Debt
    "HDFC Short Term Debt": {"category": "Short Duration", "type": "debt", "sectors": ["Debt"]},
    "ICICI Pru Corporate Bond": {"category": "Corporate Bond", "type": "debt", "sectors": ["Debt"]},
    "SBI Magnum Gilt": {"category": "Gilt", "type": "debt", "sectors": ["Debt"]},
    "HDFC Liquid Fund": {"category": "Liquid", "type": "debt", "sectors": ["Debt"]},
    "Parag Parikh Liquid": {"category": "Liquid", "type": "debt", "sectors": ["Debt"]},
    # PPF / FD treated as debt
    "PPF": {"category": "Government Savings", "type": "debt", "sectors": ["Debt"]},
    "FD": {"category": "Fixed Deposit", "type": "debt", "sectors": ["Debt"]},
    "NPS": {"category": "Pension", "type": "hybrid", "sectors": ["Diversified"]},
}

ALL_SECTORS = ["Banking", "Finance", "Insurance", "IT", "Pharma", "Healthcare",
               "FMCG", "Auto", "Conglomerate", "Oil & Gas", "Power", "Metals",
               "Telecom", "Cement", "Infrastructure", "Real Estate", "International"]


def _normalize_stock(s: dict) -> dict:
    """
    Accept either:
      {"name": ..., "value": int}                         (old: total market value)
      {"name": ..., "quantity": int, "price": float}      (new: actual shares + price)
    Returns a copy guaranteed to have "value", "quantity" (or None), "price" (or None).
    """
    s = dict(s)
    if "quantity" in s and "price" in s:
        s["value"] = int(s["quantity"] * s["price"])
    else:
        s.setdefault("quantity", None)
        s.setdefault("price", None)
    return s


def analyze_portfolio(stocks, mutual_funds, debt_investments):
    """
    Full portfolio analysis from itemized holdings.

    Args:
        stocks: list of {"name": str, "value": int}
                   OR  {"name": str, "quantity": int, "price": float}
        mutual_funds: list of {"name": str, "value": int}
        debt_investments: list of {"name": str, "value": int}

    Returns dict with:
        derived: computed features (ML-compatible)
        sector_exposure: sector -> value & percentage
        concentration: warnings about over-concentration
        mf_categories: which MF categories user already owns
        gaps: missing sectors/categories
        duplicates: any overlapping holdings
        holdings_summary: clean summary for display
    """
    stocks = [_normalize_stock(s) for s in stocks]

    # ── Compute derived features (backward compatible) ──
    stock_value = sum(s["value"] for s in stocks)
    mf_equity_value = sum(
        f["value"] for f in mutual_funds
        if MF_CATEGORIES.get(f["name"], {}).get("type", "equity") == "equity"
    )
    mf_hybrid_value = sum(
        f["value"] for f in mutual_funds
        if MF_CATEGORIES.get(f["name"], {}).get("type") == "hybrid"
    )
    mf_debt_value = sum(
        f["value"] for f in mutual_funds
        if MF_CATEGORIES.get(f["name"], {}).get("type") == "debt"
    )
    debt_value = sum(d["value"] for d in debt_investments) + mf_debt_value

    equity_value = stock_value + mf_equity_value + int(mf_hybrid_value * 0.65)
    total_debt = debt_value + int(mf_hybrid_value * 0.35)
    portfolio_total = equity_value + total_debt

    equity_pct = round((equity_value / portfolio_total * 100), 2) if portfolio_total > 0 else 0.0

    derived = {
        "current_equity_value": equity_value,
        "current_debt_value": total_debt,
        "portfolio_total": portfolio_total,
        "equity_pct": equity_pct,
        "num_stocks": len(stocks),
        "num_mutual_funds": len(mutual_funds),
        "stock_value": stock_value,
        "mf_value": sum(f["value"] for f in mutual_funds),
        "debt_value": sum(d["value"] for d in debt_investments),
    }

    # ── Sector Exposure ──
    sector_values = {}

    for s in stocks:
        sector = STOCK_SECTORS.get(s["name"], "Unknown")
        sector_values[sector] = sector_values.get(sector, 0) + s["value"]

    for f in mutual_funds:
        info = MF_CATEGORIES.get(f["name"], {})
        for sec in info.get("sectors", ["Unknown"]):
            sector_values[sec] = sector_values.get(sec, 0) + f["value"]

    sector_exposure = {}
    for sec, val in sorted(sector_values.items(), key=lambda x: x[1], reverse=True):
        pct = round((val / portfolio_total * 100), 1) if portfolio_total > 0 else 0
        sector_exposure[sec] = {"value": val, "percentage": pct}

    # ── Concentration Warnings ──
    concentration = []

    for sec, data in sector_exposure.items():
        if sec in ("Diversified", "Debt", "Unknown"):
            continue
        if data["percentage"] > 30:
            concentration.append({
                "sector": sec,
                "percentage": data["percentage"],
                "severity": "critical",
                "warning": f"{sec} at {data['percentage']}% — dangerously concentrated. Reduce to below 20%.",
            })
        elif data["percentage"] > 20:
            concentration.append({
                "sector": sec,
                "percentage": data["percentage"],
                "severity": "high",
                "warning": f"{sec} at {data['percentage']}% — over-concentrated. Consider diversifying.",
            })

    # Same-sector stock pairs
    stock_sectors = {}
    for s in stocks:
        sec = STOCK_SECTORS.get(s["name"], "Unknown")
        stock_sectors.setdefault(sec, []).append(s["name"])
    for sec, names in stock_sectors.items():
        if len(names) >= 2 and sec != "Unknown":
            concentration.append({
                "sector": sec,
                "severity": "warning",
                "warning": f"Multiple stocks in {sec}: {', '.join(names)}. Consider spreading across sectors.",
            })

    # ── MF Category Coverage ──
    owned_categories = set()
    for f in mutual_funds:
        info = MF_CATEGORIES.get(f["name"], {})
        if info.get("category"):
            owned_categories.add(info["category"])

    for d in debt_investments:
        info = MF_CATEGORIES.get(d["name"], {})
        if info.get("category"):
            owned_categories.add(info["category"])

    # ── Gaps (missing categories) ──
    ideal_equity = {"Large Cap Index", "Mid Cap", "Flexi Cap"}
    ideal_debt = {"Liquid", "Short Duration"}
    ideal_sectors = {"Banking", "IT", "Pharma", "FMCG", "Auto"}

    missing_categories = []
    for cat in ideal_equity - owned_categories:
        missing_categories.append({"category": cat, "type": "equity", "reason": f"No {cat} fund — consider adding for diversification"})
    for cat in ideal_debt - owned_categories:
        missing_categories.append({"category": cat, "type": "debt", "reason": f"No {cat} fund — useful for safety/liquidity"})

    owned_sectors = set(sector_values.keys()) - {"Diversified", "Debt", "Unknown"}
    missing_sectors = ideal_sectors - owned_sectors
    gaps = {
        "missing_fund_categories": missing_categories,
        "missing_sectors": list(missing_sectors),
    }

    # ── Duplicate Detection ──
    duplicates = []
    holding_names = [s["name"] for s in stocks] + [f["name"] for f in mutual_funds]
    seen = set()
    for name in holding_names:
        if name in seen:
            duplicates.append(f"Duplicate holding: {name}")
        seen.add(name)

    # Check if stock sector overlaps with sectoral MF
    for f in mutual_funds:
        info = MF_CATEGORIES.get(f["name"], {})
        if info.get("category") == "Sectoral":
            for sec in info.get("sectors", []):
                if sec in stock_sectors and stock_sectors[sec]:
                    duplicates.append(
                        f"{f['name']} ({sec} sectoral fund) overlaps with stocks: {', '.join(stock_sectors[sec])}"
                    )

    # ── Market Cap Distribution ──
    cap_counts = {"large_cap": 0, "mid_cap": 0, "small_cap": 0}
    cap_values = {"large_cap": 0, "mid_cap": 0, "small_cap": 0}
    for s in stocks:
        cap = STOCK_MARKET_CAP.get(s["name"], "unknown")
        if cap in cap_counts:
            cap_counts[cap] += 1
            cap_values[cap] += s["value"]

    style_counts = {"growth": 0, "value": 0, "blend": 0}
    for s in stocks:
        st = STOCK_STYLE.get(s["name"], "unknown")
        if st in style_counts:
            style_counts[st] += 1

    dividend_count = sum(1 for s in stocks if STOCK_DIVIDEND.get(s["name"], False))
    non_dividend_count = len(stocks) - dividend_count

    # ── Holdings Summary ──
    holdings_summary = {
        "stocks": [
            {
                "name": s["name"],
                "value": s["value"],
                "quantity": s.get("quantity"),   # None when not provided
                "price": s.get("price"),          # None when not provided
                "sector": STOCK_SECTORS.get(s["name"], "Unknown"),
                "market_cap": STOCK_MARKET_CAP.get(s["name"], "unknown"),
                "style": STOCK_STYLE.get(s["name"], "unknown"),
                "dividend": STOCK_DIVIDEND.get(s["name"], False),
            }
            for s in stocks
        ],
        "mutual_funds": [
            {
                "name": f["name"],
                "value": f["value"],
                "category": MF_CATEGORIES.get(f["name"], {}).get("category", "Unknown"),
                "type": MF_CATEGORIES.get(f["name"], {}).get("type", "unknown"),
            }
            for f in mutual_funds
        ],
        "debt_investments": [
            {
                "name": d["name"],
                "value": d["value"],
                "category": MF_CATEGORIES.get(d["name"], {}).get("category", "Other"),
            }
            for d in debt_investments
        ],
    }

    return {
        "derived": derived,
        "sector_exposure": sector_exposure,
        "concentration": concentration,
        "owned_mf_categories": list(owned_categories),
        "gaps": gaps,
        "duplicates": duplicates,
        "holdings_summary": holdings_summary,
        "stock_classification": {
            "by_market_cap": {
                "large_cap": {"count": cap_counts["large_cap"], "value": cap_values["large_cap"]},
                "mid_cap": {"count": cap_counts["mid_cap"], "value": cap_values["mid_cap"]},
                "small_cap": {"count": cap_counts["small_cap"], "value": cap_values["small_cap"]},
            },
            "by_style": style_counts,
            "by_dividend": {
                "dividend_stocks": dividend_count,
                "non_dividend_stocks": non_dividend_count,
            },
        },
    }
