"""
category_filter.py - Investment Category Selection & Filtering

Lets users pick what they want to invest in, then returns
filtered recommendations with sub-types, risk/return profiles,
and specific fund/stock suggestions.

Categories:
  MUTUAL FUNDS:
    1. Equity MF      (Large Cap, Mid Cap, Small Cap, Multi Cap, Sectoral, ELSS)
    2. Debt MF        (Liquid, Short Duration, Corporate Bond, Gilt)
    3. Hybrid MF      (Aggressive, Conservative, Balanced Advantage)
    4. Other MF       (Index, ETF, International, Fund of Funds)

  STOCKS:
    1. By Market Cap  (Large Cap, Mid Cap, Small Cap)
    2. By Style       (Growth, Value)
    3. By Dividend    (Dividend, Non-Dividend)
    4. By Sector      (IT, Banking, Pharma, FMCG, Auto, Energy, Metals)
    5. By Risk        (Blue Chip, Penny Stocks)
"""


# ══════════════════════════════════════════════════════════
#  MUTUAL FUND CATEGORIES
# ══════════════════════════════════════════════════════════

MF_CATEGORIES = {
    "EQUITY_MF": {
        "label": "Equity Mutual Funds",
        "icon": "E",
        "description": "Invest in stocks/shares. High risk, high return potential.",
        "best_for": "Long-term wealth creation (5+ years)",
        "risk": "High",
        "expected_return": "10-18% p.a.",
        "sub_types": {
            "Large Cap Fund": {
                "description": "Top 100 companies by market cap. Stable growth.",
                "risk": "Moderate",
                "return": "10-12% p.a.",
                "horizon": "3+ years",
                "examples": ["HDFC Top 100", "Mirae Asset Large Cap", "Axis Bluechip"],
                "best_for": "Beginners, steady growth seekers",
            },
            "Mid Cap Fund": {
                "description": "101st-250th companies. Higher growth, moderate risk.",
                "risk": "Moderate-High",
                "return": "12-15% p.a.",
                "horizon": "5+ years",
                "examples": ["Kotak Emerging Equity", "Axis Midcap", "DSP Midcap"],
                "best_for": "Intermediate investors with 5yr+ horizon",
            },
            "Small Cap Fund": {
                "description": "251st+ companies. Highest risk and return.",
                "risk": "High",
                "return": "14-18% p.a.",
                "horizon": "7+ years",
                "examples": ["SBI Small Cap", "Nippon India Small Cap", "Axis Small Cap"],
                "best_for": "Aggressive investors, long horizon only",
            },
            "Multi Cap Fund": {
                "description": "Mix of large, mid, small caps. Built-in diversification.",
                "risk": "Moderate",
                "return": "11-14% p.a.",
                "horizon": "5+ years",
                "examples": ["Parag Parikh Flexi Cap", "HDFC Flexi Cap", "Kotak Flexicap"],
                "best_for": "One-fund solution, all market cap exposure",
            },
            "Sectoral/Thematic Fund": {
                "description": "Concentrated bet on one sector (IT, Pharma, Banking).",
                "risk": "Very High",
                "return": "15-20% p.a. (volatile)",
                "horizon": "5+ years",
                "examples": ["ICICI Pru Technology", "Nippon India Pharma", "SBI Banking Fund"],
                "best_for": "Experts with sector conviction",
            },
            "ELSS (Tax Saving)": {
                "description": "Equity fund with 3yr lock-in. Tax deduction under 80C.",
                "risk": "Moderate-High",
                "return": "12-15% p.a.",
                "horizon": "3+ years (mandatory lock-in)",
                "examples": ["Axis Long Term Equity", "Mirae Asset Tax Saver", "Quant ELSS"],
                "best_for": "Tax saving + wealth creation combo",
            },
        },
    },
    "DEBT_MF": {
        "label": "Debt Mutual Funds",
        "icon": "D",
        "description": "Invest in bonds, govt securities, fixed income. Low risk.",
        "best_for": "Stability, capital preservation, short-term goals",
        "risk": "Low",
        "expected_return": "4-8% p.a.",
        "sub_types": {
            "Liquid Fund": {
                "description": "Ultra-safe, invests in <91 day instruments. Park cash.",
                "risk": "Very Low",
                "return": "4-6% p.a.",
                "horizon": "1 day+",
                "examples": ["Parag Parikh Liquid", "HDFC Liquid", "ICICI Pru Liquid"],
                "best_for": "Emergency fund, short-term parking",
            },
            "Short Duration Fund": {
                "description": "1-3 year debt instruments. Better than FD returns.",
                "risk": "Low",
                "return": "6-7% p.a.",
                "horizon": "1-3 years",
                "examples": ["HDFC Short Term Debt", "Axis Short Term", "ICICI Pru Short Term"],
                "best_for": "Short-term goals, FD alternative",
            },
            "Corporate Bond Fund": {
                "description": "High-rated corporate bonds. Stable income.",
                "risk": "Low-Moderate",
                "return": "7-8% p.a.",
                "horizon": "2+ years",
                "examples": ["ICICI Pru Corporate Bond", "HDFC Corporate Bond", "Kotak Corporate Bond"],
                "best_for": "Regular income, moderate safety",
            },
            "Gilt Fund": {
                "description": "Government securities. Zero credit risk.",
                "risk": "Low",
                "return": "6-8% p.a.",
                "horizon": "3+ years",
                "examples": ["SBI Magnum Gilt", "ICICI Pru Gilt", "Nippon India Gilt"],
                "best_for": "Zero credit risk seekers, rate cycle play",
            },
        },
    },
    "HYBRID_MF": {
        "label": "Hybrid Mutual Funds",
        "icon": "H",
        "description": "Mix of equity + debt. Balance of risk and return.",
        "best_for": "Moderate risk investors, balanced approach",
        "risk": "Medium",
        "expected_return": "7-12% p.a.",
        "sub_types": {
            "Aggressive Hybrid Fund": {
                "description": "65-80% equity + 20-35% debt. Growth with cushion.",
                "risk": "Moderate",
                "return": "10-12% p.a.",
                "horizon": "3+ years",
                "examples": ["Canara Robeco Equity Hybrid", "Mirae Asset Hybrid Equity"],
                "best_for": "First-time equity investors wanting safety net",
            },
            "Conservative Hybrid Fund": {
                "description": "75-90% debt + 10-25% equity. Income-focused.",
                "risk": "Low-Moderate",
                "return": "7-9% p.a.",
                "horizon": "2+ years",
                "examples": ["SBI Conservative Hybrid", "HDFC Hybrid Debt"],
                "best_for": "Retirees, income seekers with small equity kicker",
            },
            "Balanced Advantage Fund": {
                "description": "Auto-adjusts equity/debt ratio. All-weather fund.",
                "risk": "Moderate",
                "return": "9-11% p.a.",
                "horizon": "3+ years",
                "examples": ["ICICI Pru BAF", "HDFC BAF", "Edelweiss BAF"],
                "best_for": "Hands-off investors, all market conditions",
            },
        },
    },
    "OTHER_MF": {
        "label": "Other / Special Mutual Funds",
        "icon": "O",
        "description": "Index tracking, international, and fund-of-funds.",
        "best_for": "Passive investing, global diversification",
        "risk": "Varies",
        "expected_return": "8-16% p.a.",
        "sub_types": {
            "Index Fund": {
                "description": "Tracks Nifty 50 or Sensex passively. Lowest cost.",
                "risk": "Moderate",
                "return": "10-12% p.a.",
                "horizon": "3+ years",
                "examples": ["UTI Nifty 50 Index", "HDFC Index Fund Nifty 50"],
                "best_for": "Cost-conscious, long-term passive investors",
            },
            "ETF (Exchange Traded Fund)": {
                "description": "Trades on stock exchange like a stock. Low expense ratio.",
                "risk": "Moderate",
                "return": "10-12% p.a.",
                "horizon": "3+ years",
                "examples": ["Nippon India Nifty ETF", "SBI Nifty 50 ETF"],
                "best_for": "Active traders wanting index exposure",
            },
            "International Fund": {
                "description": "Invests in US/global markets. Geographic diversification.",
                "risk": "Moderate-High",
                "return": "12-16% p.a.",
                "horizon": "5+ years",
                "examples": ["Motilal Oswal Nasdaq 100", "Franklin India Feeder US"],
                "best_for": "Global diversification, USD exposure",
            },
            "Fund of Funds (FoF)": {
                "description": "Invests in other mutual funds. Multi-strategy approach.",
                "risk": "Varies",
                "return": "8-14% p.a.",
                "horizon": "3+ years",
                "examples": ["ICICI Pru Asset Allocator FoF", "Nippon India FoF"],
                "best_for": "Hands-off, multi-asset allocation",
            },
        },
    },
}


# ══════════════════════════════════════════════════════════
#  STOCK CATEGORIES
# ══════════════════════════════════════════════════════════

STOCK_CATEGORIES = {
    "BY_MARKET_CAP": {
        "label": "By Market Capitalization",
        "icon": "M",
        "description": "Classification by company size",
        "sub_types": {
            "Large Cap": {
                "description": "Top 100 companies. Stable, low risk, steady returns.",
                "risk": "Low-Moderate",
                "return": "10-14% p.a.",
                "examples": ["Reliance", "TCS", "HDFC Bank", "Infosys", "ITC"],
                "best_for": "Safety with growth, beginners",
            },
            "Mid Cap": {
                "description": "101st-250th companies. Growing, medium risk.",
                "risk": "Moderate-High",
                "return": "14-20% p.a.",
                "examples": ["Bajaj Auto", "Cipla", "Dr Reddy's", "Dabur", "M&M"],
                "best_for": "Growth seekers with 5yr+ horizon",
            },
            "Small Cap": {
                "description": "251st+ companies. High risk, high reward potential.",
                "risk": "High",
                "return": "18-30% p.a. (volatile)",
                "examples": ["DLF", "Adani Green", "Godrej Properties"],
                "best_for": "Aggressive investors, long-term only",
            },
        },
    },
    "BY_STYLE": {
        "label": "By Investment Style",
        "icon": "S",
        "description": "Growth vs Value investing approach",
        "sub_types": {
            "Growth Stocks": {
                "description": "Fast-growing companies. Reinvest profits, no/low dividend.",
                "risk": "Moderate-High",
                "return": "15-25% p.a.",
                "examples": ["TCS", "Infosys", "Bajaj Finance", "Divi's Labs"],
                "best_for": "Capital appreciation, long-term wealth",
            },
            "Value Stocks": {
                "description": "Undervalued companies. Cheap price vs actual worth.",
                "risk": "Moderate",
                "return": "12-18% p.a.",
                "examples": ["ITC", "ONGC", "SBI", "Tata Steel", "NTPC"],
                "best_for": "Patient investors, contrarian plays",
            },
        },
    },
    "BY_DIVIDEND": {
        "label": "By Dividend Payout",
        "icon": "D",
        "description": "Regular income vs pure growth",
        "sub_types": {
            "Dividend Stocks": {
                "description": "Pay regular dividends. Stable income + capital growth.",
                "risk": "Low-Moderate",
                "return": "8-14% p.a. + 2-5% dividend yield",
                "examples": ["ITC", "NTPC", "Power Grid", "Coal India", "HUL"],
                "best_for": "Income seekers, retirees, conservative investors",
            },
            "Non-Dividend (Growth) Stocks": {
                "description": "No dividend. All profits reinvested for growth.",
                "risk": "Moderate-High",
                "return": "15-25% p.a. (capital gains only)",
                "examples": ["Bajaj Finance", "Adani Green", "DLF", "Apollo Hospitals"],
                "best_for": "Pure growth, don't need regular income",
            },
        },
    },
    "BY_SECTOR": {
        "label": "By Sector / Industry",
        "icon": "I",
        "description": "Industry-specific stock picks",
        "sub_types": {
            "Banking & Finance": {
                "description": "Banks, NBFCs, insurance companies. Economy backbone.",
                "risk": "Moderate",
                "return": "12-18% p.a.",
                "examples": ["HDFC Bank", "ICICI Bank", "SBI", "Bajaj Finance", "Kotak Bank"],
                "best_for": "India growth story, credit expansion play",
            },
            "IT / Technology": {
                "description": "Software, services, tech companies. Global revenue.",
                "risk": "Moderate",
                "return": "12-20% p.a.",
                "examples": ["TCS", "Infosys", "Wipro", "HCL Tech", "Tech Mahindra"],
                "best_for": "USD earnings exposure, global demand",
            },
            "Pharma & Healthcare": {
                "description": "Drug makers, hospitals. Defensive sector.",
                "risk": "Moderate",
                "return": "12-16% p.a.",
                "examples": ["Sun Pharma", "Dr Reddy's", "Cipla", "Apollo Hospitals"],
                "best_for": "Defensive play, ageing population trend",
            },
            "FMCG": {
                "description": "Daily consumer goods. Recession-proof, steady demand.",
                "risk": "Low",
                "return": "10-14% p.a.",
                "examples": ["HUL", "ITC", "Nestle", "Britannia", "Dabur"],
                "best_for": "Stability, inflation hedge, safe haven",
            },
            "Auto": {
                "description": "Car, bike, truck manufacturers. Cyclical sector.",
                "risk": "Moderate-High",
                "return": "14-22% p.a.",
                "examples": ["Maruti", "Tata Motors", "M&M", "Bajaj Auto", "Eicher Motors"],
                "best_for": "Economic recovery play, EV transition bet",
            },
            "Energy & Power": {
                "description": "Oil, gas, power generation, renewable energy.",
                "risk": "Moderate",
                "return": "10-16% p.a.",
                "examples": ["Reliance", "ONGC", "NTPC", "Power Grid", "Adani Green"],
                "best_for": "Dividend income, infrastructure growth",
            },
            "Metals & Mining": {
                "description": "Steel, aluminum, mining. Commodity-linked, cyclical.",
                "risk": "High",
                "return": "15-25% p.a. (cyclical)",
                "examples": ["Tata Steel", "Hindalco", "JSW Steel"],
                "best_for": "Commodity cycle play, infrastructure boom",
            },
        },
    },
    "BY_RISK": {
        "label": "By Risk Profile",
        "icon": "R",
        "description": "Safety-first vs high-risk-high-reward",
        "sub_types": {
            "Blue Chip Stocks": {
                "description": "Trusted, established market leaders. Most stable.",
                "risk": "Low",
                "return": "10-14% p.a.",
                "examples": ["Reliance", "TCS", "HDFC Bank", "HUL", "Infosys"],
                "best_for": "Core portfolio, beginners, retirement funds",
            },
            "Penny Stocks": {
                "description": "Very cheap stocks (INR 10-50). Extremely risky.",
                "risk": "Very High",
                "return": "Can 10x or go to zero",
                "examples": ["Varies — high turnover, no stable examples"],
                "best_for": "Gambling money only, never core portfolio",
            },
        },
    },
}


# ══════════════════════════════════════════════════════════
#  QUICK RISK-BASED CATEGORY SUGGESTION
# ══════════════════════════════════════════════════════════

def suggest_categories(risk_level, goal_years, investment_experience):
    """
    Suggest which categories fit the user based on risk, goal, experience.
    Returns dict with:
        primary: recommended main category
        mf_types: list of suitable MF sub-types
        stock_types: list of suitable stock sub-types
        avoid: list of categories to avoid
    """
    mf_types = []
    stock_types = []
    avoid = []

    if risk_level == "low":
        primary = "DEBT_MF"
        mf_types = ["Liquid Fund", "Short Duration Fund", "Gilt Fund",
                     "Conservative Hybrid Fund", "Large Cap Fund", "Index Fund"]
        stock_types = ["Blue Chip Stocks", "Dividend Stocks", "Large Cap"]
        avoid = ["Small Cap Fund", "Sectoral/Thematic Fund", "Penny Stocks",
                 "Small Cap", "Non-Dividend (Growth) Stocks"]

    elif risk_level == "medium":
        primary = "HYBRID_MF"
        mf_types = ["Balanced Advantage Fund", "Aggressive Hybrid Fund",
                     "Large Cap Fund", "Multi Cap Fund", "Index Fund", "Mid Cap Fund",
                     "Corporate Bond Fund", "ELSS (Tax Saving)"]
        stock_types = ["Large Cap", "Mid Cap", "Growth Stocks", "Value Stocks",
                       "Dividend Stocks", "Blue Chip Stocks"]
        avoid = ["Small Cap Fund", "Penny Stocks", "Sectoral/Thematic Fund"]

    else:  # high
        primary = "EQUITY_MF"
        mf_types = ["Mid Cap Fund", "Small Cap Fund", "Multi Cap Fund",
                     "Sectoral/Thematic Fund", "International Fund", "ELSS (Tax Saving)"]
        stock_types = ["Mid Cap", "Small Cap", "Growth Stocks",
                       "Non-Dividend (Growth) Stocks"]
        avoid = ["Conservative Hybrid Fund", "Liquid Fund", "Gilt Fund"]

    # Goal-based filtering
    if goal_years <= 2:
        mf_types = [t for t in mf_types if t in
                    ["Liquid Fund", "Short Duration Fund", "Conservative Hybrid Fund"]]
        if not mf_types:
            mf_types = ["Liquid Fund"]
        stock_types = ["Dividend Stocks", "Blue Chip Stocks"]
        avoid.extend(["Small Cap Fund", "Mid Cap Fund", "Small Cap"])

    elif goal_years <= 5:
        mf_types = [t for t in mf_types if t not in
                    ["Small Cap Fund", "Sectoral/Thematic Fund"]]
        stock_types = [t for t in stock_types if t not in ["Small Cap"]]

    # Experience-based filtering
    if investment_experience == "beginner":
        mf_types = [t for t in mf_types if t not in
                    ["Sectoral/Thematic Fund", "ETF (Exchange Traded Fund)"]]
        stock_types = [t for t in stock_types if t not in
                       ["Small Cap", "Non-Dividend (Growth) Stocks", "Penny Stocks"]]
        avoid.extend(["Sectoral/Thematic Fund", "Penny Stocks", "Small Cap"])

    # Deduplicate avoid
    avoid = list(dict.fromkeys(avoid))

    return {
        "primary": primary,
        "primary_label": MF_CATEGORIES[primary]["label"],
        "mf_types": mf_types,
        "stock_types": stock_types,
        "avoid": avoid,
    }


# ══════════════════════════════════════════════════════════
#  CATEGORY DETAIL LOOKUP
# ══════════════════════════════════════════════════════════

def get_mf_category_detail(category_key):
    """Get full details for a MF category (EQUITY_MF, DEBT_MF, etc.)"""
    return MF_CATEGORIES.get(category_key)


def get_mf_subtype_detail(subtype_name):
    """Find a MF sub-type across all categories."""
    for cat_key, cat in MF_CATEGORIES.items():
        if subtype_name in cat["sub_types"]:
            return {
                "category": cat_key,
                "category_label": cat["label"],
                **cat["sub_types"][subtype_name],
            }
    return None


def get_stock_subtype_detail(subtype_name):
    """Find a stock sub-type across all categories."""
    for cat_key, cat in STOCK_CATEGORIES.items():
        if subtype_name in cat["sub_types"]:
            return {
                "category": cat_key,
                "category_label": cat["label"],
                **cat["sub_types"][subtype_name],
            }
    return None


def get_all_mf_menu():
    """Return the full MF category menu for display."""
    menu = []
    for key, cat in MF_CATEGORIES.items():
        item = {
            "key": key,
            "label": cat["label"],
            "risk": cat["risk"],
            "return": cat["expected_return"],
            "best_for": cat["best_for"],
            "sub_types": list(cat["sub_types"].keys()),
        }
        menu.append(item)
    return menu


def get_all_stock_menu():
    """Return the full stock category menu for display."""
    menu = []
    for key, cat in STOCK_CATEGORIES.items():
        item = {
            "key": key,
            "label": cat["label"],
            "sub_types": list(cat["sub_types"].keys()),
        }
        menu.append(item)
    return menu
