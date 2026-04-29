"""
recommendation_engine.py - Deterministic Recommendation Engine

No LLM. No hallucination. No API cost. Pure logic.

Maps: ML Action + Risk Level + Goal Years → Investment Category + Fund Types

Flow:
  Action → Category → Risk Filter → Goal Filter → Final Recommendation
"""


# ──────────────────────────────────────────────
#  Fund Type Knowledge Base
# ──────────────────────────────────────────────

FUND_DESCRIPTIONS = {
    # Equity
    "Large Cap Fund": {
        "description": "Invests in top 100 companies by market cap. Stable growth with lower volatility.",
        "risk": "low",
        "min_horizon": "3+ years",
        "expected_return": "10-12% p.a.",
        "examples": ["HDFC Top 100", "Mirae Asset Large Cap", "Axis Bluechip"],
    },
    "Index Fund": {
        "description": "Tracks Nifty 50 or Sensex passively. Lowest cost, market-matching returns.",
        "risk": "low",
        "min_horizon": "3+ years",
        "expected_return": "10-12% p.a.",
        "examples": ["UTI Nifty 50 Index", "HDFC Index Fund Nifty 50", "Nippon India Index Nifty"],
    },
    "Mid Cap Fund": {
        "description": "Invests in 101st-250th companies. Higher growth potential with moderate risk.",
        "risk": "moderate",
        "min_horizon": "5+ years",
        "expected_return": "12-15% p.a.",
        "examples": ["Kotak Emerging Equity", "Axis Midcap", "DSP Midcap"],
    },
    "Small Cap Fund": {
        "description": "Invests in 251st+ companies. High risk, high reward for patient investors.",
        "risk": "high",
        "min_horizon": "7+ years",
        "expected_return": "14-18% p.a.",
        "examples": ["SBI Small Cap", "Nippon India Small Cap", "Axis Small Cap"],
    },
    "Multi Cap Fund": {
        "description": "Invests across large, mid, and small caps. Built-in diversification.",
        "risk": "moderate",
        "min_horizon": "5+ years",
        "expected_return": "11-14% p.a.",
        "examples": ["Parag Parikh Flexi Cap", "HDFC Flexi Cap", "Kotak Flexicap"],
    },
    "Flexi Cap Fund": {
        "description": "Fund manager picks across all market caps based on opportunity.",
        "risk": "moderate",
        "min_horizon": "5+ years",
        "expected_return": "11-14% p.a.",
        "examples": ["Parag Parikh Flexi Cap", "SBI Flexi Cap", "PGIM India Flexi Cap"],
    },
    "Sectoral Fund": {
        "description": "Concentrated bet on one sector (IT, pharma, banking). Very high risk.",
        "risk": "very_high",
        "min_horizon": "5+ years",
        "expected_return": "15-20% p.a. (volatile)",
        "examples": ["ICICI Pru Technology", "Nippon India Pharma", "SBI Banking & Financial"],
    },
    "International Fund": {
        "description": "Invests in global markets (US, Nasdaq). Geographic diversification.",
        "risk": "moderate",
        "min_horizon": "5+ years",
        "expected_return": "12-16% p.a.",
        "examples": ["Motilal Oswal Nasdaq 100", "Franklin India Feeder US Opp", "PGIM India Global Equity"],
    },
    # Debt
    "Liquid Fund": {
        "description": "Ultra-safe, invests in <91 day instruments. Best for emergency fund or parking cash.",
        "risk": "very_low",
        "min_horizon": "1 day+",
        "expected_return": "4-6% p.a.",
        "examples": ["Parag Parikh Liquid", "HDFC Liquid", "ICICI Pru Liquid"],
    },
    "Short Duration Fund": {
        "description": "Invests in 1-3 year debt instruments. Slightly better returns than liquid.",
        "risk": "low",
        "min_horizon": "1+ years",
        "expected_return": "6-7% p.a.",
        "examples": ["HDFC Short Term Debt", "Axis Short Term", "ICICI Pru Short Term"],
    },
    "Corporate Bond Fund": {
        "description": "Invests in high-rated corporate bonds. Stable income with moderate returns.",
        "risk": "low",
        "min_horizon": "2+ years",
        "expected_return": "7-8% p.a.",
        "examples": ["ICICI Pru Corporate Bond", "HDFC Corporate Bond", "Kotak Corporate Bond"],
    },
    "Gilt Fund": {
        "description": "Invests in government securities. Zero credit risk, interest rate sensitive.",
        "risk": "low",
        "min_horizon": "3+ years",
        "expected_return": "6-8% p.a.",
        "examples": ["SBI Magnum Gilt", "ICICI Pru Gilt", "Nippon India Gilt"],
    },
    # Hybrid
    "Balanced Advantage Fund": {
        "description": "Auto-adjusts equity/debt ratio based on market conditions. All-weather fund.",
        "risk": "moderate",
        "min_horizon": "3+ years",
        "expected_return": "9-11% p.a.",
        "examples": ["ICICI Pru BAF", "HDFC BAF", "Edelweiss BAF"],
    },
    "Aggressive Hybrid Fund": {
        "description": "65-80% equity + 20-35% debt. Growth with stability cushion.",
        "risk": "moderate",
        "min_horizon": "3+ years",
        "expected_return": "10-12% p.a.",
        "examples": ["Canara Robeco Equity Hybrid", "Mirae Asset Hybrid Equity", "SBI Equity Hybrid"],
    },
    "Conservative Hybrid Fund": {
        "description": "75-90% debt + 10-25% equity. Income-focused with small equity kicker.",
        "risk": "low",
        "min_horizon": "2+ years",
        "expected_return": "7-9% p.a.",
        "examples": ["SBI Conservative Hybrid", "HDFC Hybrid Debt", "ICICI Pru Regular Savings"],
    },
}


# ──────────────────────────────────────────────
#  Step 1: Action → Category
# ──────────────────────────────────────────────

def _get_category(action):
    """Map ML action to investment category."""
    MAPPING = {
        "START_SIP":            "EQUITY",
        "INCREASE_SIP":         "EQUITY",
        "CONTINUE_SIP":         "EQUITY",
        "BUY":                  "EQUITY",
        "SWITCH_TO_EQUITY":     "EQUITY",
        "SWITCH_TO_DEBT":       "DEBT",
        "REBALANCE":            "HYBRID",
        "DIVERSIFY_PORTFOLIO":  "DIVERSIFIED",
        "EMERGENCY_FUND_BUILD": "LIQUID",
        "STOP_SIP":             "LIQUID",
        "REDUCE_SIP":           "DEBT",
        "SELL":                 "DEBT",
        "HOLD":                 "HOLD",
    }
    return MAPPING.get(action, "HOLD")


# ──────────────────────────────────────────────
#  Step 2: Risk-Based Filtering
# ──────────────────────────────────────────────

def _refine_by_risk(category, risk_level):
    """Filter fund types based on risk tolerance."""
    if category == "EQUITY":
        if risk_level == "low":
            return ["Large Cap Fund", "Index Fund"]
        elif risk_level == "medium":
            return ["Large Cap Fund", "Index Fund", "Mid Cap Fund", "Multi Cap Fund"]
        else:  # high
            return ["Mid Cap Fund", "Small Cap Fund", "Multi Cap Fund", "Sectoral Fund", "International Fund"]

    elif category == "DEBT":
        if risk_level == "low":
            return ["Liquid Fund", "Short Duration Fund", "Gilt Fund"]
        elif risk_level == "medium":
            return ["Short Duration Fund", "Corporate Bond Fund", "Gilt Fund"]
        else:
            return ["Corporate Bond Fund", "Short Duration Fund"]

    elif category == "HYBRID":
        if risk_level == "low":
            return ["Conservative Hybrid Fund", "Balanced Advantage Fund"]
        elif risk_level == "medium":
            return ["Balanced Advantage Fund", "Aggressive Hybrid Fund"]
        else:
            return ["Aggressive Hybrid Fund", "Balanced Advantage Fund"]

    elif category == "DIVERSIFIED":
        if risk_level == "low":
            return ["Large Cap Fund", "Index Fund", "Balanced Advantage Fund", "Corporate Bond Fund"]
        elif risk_level == "medium":
            return ["Multi Cap Fund", "Mid Cap Fund", "Balanced Advantage Fund", "Corporate Bond Fund"]
        else:
            return ["Multi Cap Fund", "Small Cap Fund", "International Fund", "Corporate Bond Fund"]

    elif category == "LIQUID":
        return ["Liquid Fund"]

    return []


# ──────────────────────────────────────────────
#  Step 3: Goal-Based Filtering
# ──────────────────────────────────────────────

def _refine_by_goal(types, goal_years):
    """Filter based on investment horizon."""
    if goal_years <= 2:
        safe = ["Liquid Fund", "Short Duration Fund", "Conservative Hybrid Fund"]
        filtered = [t for t in types if t in safe]
        return filtered if filtered else ["Liquid Fund"]

    elif goal_years <= 5:
        exclude = ["Small Cap Fund", "Sectoral Fund"]
        filtered = [t for t in types if t not in exclude]
        return filtered if filtered else types

    else:  # 5+ years — allow everything
        return types


# ──────────────────────────────────────────────
#  Step 4: Build Allocation
# ──────────────────────────────────────────────

def _compute_allocation(types, category, risk_level):
    """Compute percentage allocation across fund types."""
    n = len(types)
    if n == 0:
        return []

    if n == 1:
        return [{"type": types[0], "allocation": 100}]

    # Smart allocation based on category
    if category in ("EQUITY", "DIVERSIFIED"):
        if n == 2:
            return [
                {"type": types[0], "allocation": 60},
                {"type": types[1], "allocation": 40},
            ]
        elif n == 3:
            return [
                {"type": types[0], "allocation": 40},
                {"type": types[1], "allocation": 35},
                {"type": types[2], "allocation": 25},
            ]
        else:
            # First gets most, rest split evenly
            first = 35
            rest = (100 - first) // (n - 1)
            allocs = [{"type": types[0], "allocation": first}]
            for i, t in enumerate(types[1:]):
                alloc = rest if i < n - 2 else 100 - first - rest * (n - 2)
                allocs.append({"type": t, "allocation": alloc})
            return allocs

    elif category in ("DEBT", "HYBRID"):
        if n == 2:
            return [
                {"type": types[0], "allocation": 50},
                {"type": types[1], "allocation": 50},
            ]
        else:
            each = 100 // n
            allocs = [{"type": t, "allocation": each} for t in types[:-1]]
            allocs.append({"type": types[-1], "allocation": 100 - each * (n - 1)})
            return allocs

    # Default: equal split
    each = 100 // n
    allocs = [{"type": t, "allocation": each} for t in types[:-1]]
    allocs.append({"type": types[-1], "allocation": 100 - each * (n - 1)})
    return allocs


# ──────────────────────────────────────────────
#  Main: Deterministic Recommendation
# ──────────────────────────────────────────────

CATEGORY_LABELS = {
    "EQUITY": "Equity Mutual Funds",
    "DEBT": "Debt Mutual Funds",
    "HYBRID": "Hybrid Mutual Funds",
    "DIVERSIFIED": "Diversified Portfolio (Equity + Debt + Hybrid)",
    "LIQUID": "Liquid / Ultra-Safe Funds",
    "HOLD": "No new investment needed",
}

CATEGORY_BEST_FOR = {
    "EQUITY": "Long-term wealth creation (5+ years)",
    "DEBT": "Capital preservation and stable income (1-3 years)",
    "HYBRID": "Balanced growth with downside protection (3-5 years)",
    "DIVERSIFIED": "All-weather portfolio across asset classes",
    "LIQUID": "Emergency fund parking and short-term safety",
    "HOLD": "Current portfolio is well-positioned",
}


def get_recommendation(action, risk_level, goal_years):
    """
    Deterministic recommendation engine.
    No LLM. No API. No hallucination. Pure logic.

    Returns complete recommendation with category, fund types,
    allocations, descriptions, and examples.
    """
    category = _get_category(action)

    if category == "HOLD":
        return {
            "action": action,
            "category": category,
            "category_label": CATEGORY_LABELS[category],
            "best_for": CATEGORY_BEST_FOR[category],
            "fund_types": [],
            "allocation": [],
        }

    types = _refine_by_risk(category, risk_level)
    types = _refine_by_goal(types, goal_years)
    allocation = _compute_allocation(types, category, risk_level)

    fund_types = []
    for a in allocation:
        t = a["type"]
        info = FUND_DESCRIPTIONS.get(t, {})
        fund_types.append({
            "type": t,
            "allocation": f"{a['allocation']}%",
            "description": info.get("description", ""),
            "risk": info.get("risk", ""),
            "min_horizon": info.get("min_horizon", ""),
            "expected_return": info.get("expected_return", ""),
            "examples": info.get("examples", []),
        })

    return {
        "action": action,
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "best_for": CATEGORY_BEST_FOR[category],
        "fund_types": fund_types,
        "allocation": allocation,
    }
