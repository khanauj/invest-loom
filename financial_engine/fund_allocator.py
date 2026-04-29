"""
fund_allocator.py - Split total SIP across specific named funds with percentages

Given: total SIP amount + risk level + goal type + horizon
Returns: "Put INR 3,200 into UTI Nifty 50, INR 2,400 into Axis Midcap, ..."

Allocation templates:
  risk × horizon bucket → [(category, weight%)]
  goal overrides for emergency_fund, education, retirement, etc.
"""

from typing import Optional
from .fund_database import get_funds_by_category, CATEGORY_MAP

# ── Allocation templates ───────────────────────────────────────────────────────
# (category, weight%) pairs. Weights must sum to 100.

TEMPLATES = {
    "low": {
        "short":  [("liquid", 50), ("debt", 40), ("gold", 10)],
        "medium": [("large_cap", 25), ("debt", 45), ("liquid", 15), ("gold", 15)],
        "long":   [("large_cap", 40), ("debt", 35), ("balanced_advantage", 15), ("gold", 10)],
    },
    "medium": {
        "short":  [("liquid", 30), ("debt", 45), ("balanced_advantage", 25)],
        "medium": [("large_cap", 35), ("mid_cap", 15), ("debt", 25), ("balanced_advantage", 15), ("gold", 10)],
        "long":   [("large_cap", 30), ("mid_cap", 20), ("small_cap", 10),
                   ("flexi_cap", 15), ("debt", 10), ("international", 10), ("gold", 5)],
    },
    "high": {
        "short":  [("large_cap", 45), ("debt", 35), ("balanced_advantage", 20)],
        "medium": [("large_cap", 25), ("mid_cap", 30), ("small_cap", 20),
                   ("international", 15), ("debt", 10)],
        "long":   [("large_cap", 20), ("mid_cap", 25), ("small_cap", 20),
                   ("flexi_cap", 15), ("international", 12), ("gold", 5), ("elss", 3)],
    },
}

GOAL_OVERRIDES = {
    "emergency_fund": [("liquid", 70), ("debt", 30)],
    "education":      [("large_cap", 35), ("mid_cap", 20), ("elss", 20), ("debt", 25)],
    "retirement":     [("large_cap", 25), ("mid_cap", 20), ("small_cap", 10),
                       ("elss", 20), ("international", 10), ("gold", 10), ("debt", 5)],
    "house":          [("debt", 40), ("large_cap", 30), ("balanced_advantage", 20), ("gold", 10)],
    "wedding":        [("debt", 50), ("large_cap", 30), ("balanced_advantage", 20)],
    "tax_saving":     [("elss", 60), ("large_cap", 30), ("debt", 10)],
    "vacation":       [("liquid", 40), ("debt", 40), ("balanced_advantage", 20)],
}


def _horizon_bucket(years: int) -> str:
    if years <= 3:  return "short"
    if years <= 7:  return "medium"
    return "long"


def _best_fund(category: str, prefer_low_cost: bool = False,
               exclude_names: set = None) -> dict:
    """
    Select best fund from a category — by 5yr return or lowest expense ratio.
    Skips any fund whose name is in exclude_names (already held by user).
    Falls back to the best fund with an already_held flag if no alternative exists.
    """
    funds = get_funds_by_category(category)
    if not funds:
        return {}
    key = "expense_ratio" if prefer_low_cost else "returns_5yr"
    reverse = not prefer_low_cost
    ranked = sorted(funds, key=lambda f: f.get(key, 0), reverse=reverse)

    if not exclude_names:
        return ranked[0]

    # Prefer a fund the user does NOT already hold
    for fund in ranked:
        if fund.get("name", "") not in exclude_names:
            return fund

    # All funds in this category are already held — return best with flag
    best = ranked[0]
    return {**best, "already_held": True}


# ── Public API ─────────────────────────────────────────────────────────────────

def allocate_sip(
    total_sip: float,
    risk_level: str = "medium",
    goal_type: str = "wealth",
    horizon_years: int = 10,
    prefer_low_cost: bool = False,
    existing_sip_funds: list = None,
) -> dict:
    """
    Split total_sip across specific recommended funds.

    Parameters
    ----------
    total_sip           : Total monthly SIP amount in INR
    risk_level          : low / medium / high
    goal_type           : wealth / education / retirement / house / wedding /
                          emergency_fund / tax_saving / vacation
    horizon_years       : Investment horizon in years
    prefer_low_cost     : If True, pick lowest expense ratio fund per category
    existing_sip_funds  : List of fund names the user already has active SIPs in.
                          The allocator will skip these and pick the next-best fund
                          in each category to avoid duplicate SIP suggestions.

    Returns
    -------
    dict with allocations list, blended_return, num_funds, summary
    """
    risk_level = risk_level.lower()
    goal_type  = goal_type.lower()

    # Normalise existing SIP fund names to a set for O(1) lookup
    exclude_names = set(existing_sip_funds) if existing_sip_funds else set()

    # Pick template
    if goal_type in GOAL_OVERRIDES:
        template = GOAL_OVERRIDES[goal_type]
    else:
        bucket    = _horizon_bucket(horizon_years)
        templates = TEMPLATES.get(risk_level, TEMPLATES["medium"])
        template  = templates.get(bucket, templates["long"])

    allocations = []
    for category, pct in template:
        fund = _best_fund(category, prefer_low_cost, exclude_names=exclude_names)
        if not fund:
            continue

        raw_amount = round(total_sip * pct / 100)
        # Honour minimum SIP floor
        amount = max(raw_amount, fund.get("min_sip", 100))

        already_held = fund.get("already_held", False)
        allocations.append({
            "fund_name":     fund["name"],
            "fund_house":    fund["fund_house"],
            "category":      category,
            "fund_type":     fund["fund_type"],
            "risk":          fund["risk"],
            "sip_amount":    amount,
            "percentage":    pct,
            "expense_ratio": fund["expense_ratio"],
            "returns_1yr":   fund["returns_1yr"],
            "returns_3yr":   fund["returns_3yr"],
            "returns_5yr":   fund["returns_5yr"],
            "min_sip":       fund["min_sip"],
            "best_for":      fund["best_for"],
            "already_held":  already_held,
            "note":          "You already hold this fund — consider topping up existing SIP instead of starting a new one." if already_held else None,
        })

    # Fix rounding so amounts sum to total_sip
    allocated = sum(a["sip_amount"] for a in allocations)
    diff      = round(total_sip) - allocated
    if allocations and diff != 0:
        allocations[0]["sip_amount"] += diff

    # Blended expected return (weighted average of 5yr returns)
    total_weight = sum(a["percentage"] for a in allocations)
    blended = (
        sum(a["percentage"] * a["returns_5yr"] for a in allocations) / total_weight
        if total_weight > 0 else 0.0
    )

    return {
        "total_sip":      round(total_sip),
        "risk_level":     risk_level,
        "goal_type":      goal_type,
        "horizon_years":  horizon_years,
        "num_funds":      len(allocations),
        "allocations":    allocations,
        "blended_return": round(blended, 2),
        "summary": (
            f"INR {total_sip:,.0f}/mo across {len(allocations)} funds "
            f"| Blended CAGR: {blended:.1f}% | Risk: {risk_level}"
        ),
    }
