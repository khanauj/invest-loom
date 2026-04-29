"""
rebalancing_engine.py - Portfolio rebalancing with specific buy/sell instructions

Generates:
- Current vs target allocation comparison
- Specific "sell X shares of A, buy Y of B" instructions
- Tax-efficient ordering (LTCG before STCG sells)
- Suggested instruments per asset class
"""

import math
from typing import List, Optional


# Default target allocations by risk level (fractions sum to 1.0)
DEFAULT_TARGETS = {
    "low": {
        "large_cap_equity": 0.20,
        "mid_cap_equity":   0.05,
        "debt_funds":       0.40,
        "liquid_funds":     0.15,
        "gold":             0.10,
        "international":    0.10,
    },
    "medium": {
        "large_cap_equity": 0.35,
        "mid_cap_equity":   0.15,
        "small_cap_equity": 0.05,
        "debt_funds":       0.25,
        "liquid_funds":     0.10,
        "gold":             0.05,
        "international":    0.05,
    },
    "high": {
        "large_cap_equity": 0.30,
        "mid_cap_equity":   0.25,
        "small_cap_equity": 0.15,
        "debt_funds":       0.10,
        "liquid_funds":     0.05,
        "gold":             0.05,
        "international":    0.10,
    },
}

_LARGE_CAPS = {
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
    "BHARTIARTL", "KOTAKBANK", "LT", "BAJFINANCE", "SBIN", "ASIANPAINT",
    "TITAN", "HCLTECH", "WIPRO", "AXISBANK", "NESTLEIND", "MARUTI",
}

_INSTRUMENT_SUGGESTIONS = {
    "large_cap_equity": [
        "Nifty 50 Index Fund", "ICICI Pru Bluechip Fund", "Mirae Asset Large Cap Fund"
    ],
    "mid_cap_equity": [
        "Nifty Midcap 150 Index Fund", "Kotak Emerging Equity Fund", "Axis Midcap Fund"
    ],
    "small_cap_equity": [
        "Nifty Smallcap 250 Index Fund", "SBI Small Cap Fund", "Nippon India Small Cap Fund"
    ],
    "debt_funds": [
        "HDFC Short Duration Fund", "Kotak Bond Fund", "G-Sec Index Fund"
    ],
    "liquid_funds": [
        "ICICI Pru Liquid Fund", "Axis Liquid Fund", "HDFC Liquid Fund"
    ],
    "gold": [
        "Sovereign Gold Bond (SGB)", "Nippon India Gold ETF", "HDFC Gold ETF"
    ],
    "international": [
        "Motilal Oswal Nasdaq 100 FOF", "Parag Parikh Flexi Cap Fund"
    ],
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _auto_category(ticker: str, asset_type: str = "stock") -> str:
    """Best-effort category from ticker and asset_type hint."""
    asset_type = (asset_type or "stock").lower()
    if asset_type in ("liquid", "liquid_fund"):  return "liquid_funds"
    if asset_type in ("gold", "goldetf"):         return "gold"
    if asset_type == "international":             return "international"
    if asset_type == "debt":                      return "debt_funds"

    base = ticker.upper().replace(".NS", "").replace(".BO", "")
    if base in _LARGE_CAPS:
        return "large_cap_equity"
    return "mid_cap_equity"


# ── Core functions ─────────────────────────────────────────────────────────────

def calculate_current_allocation(holdings: List[dict]) -> dict:
    """
    Summarise current portfolio by asset category.

    Each holding dict: {ticker, quantity, current_price, category (optional), asset_type (optional)}
    Returns: {total_value, categories: {cat: {value, percentage}}}
    """
    if not holdings:
        return {"total_value": 0, "categories": {}}

    cat_values: dict = {}
    for h in holdings:
        qty   = h.get("quantity", 0)
        price = h.get("current_price", 0)
        value = qty * price
        cat   = h.get("category") or _auto_category(h.get("ticker", ""), h.get("asset_type", "stock"))
        cat_values[cat] = cat_values.get(cat, 0) + value

    total = sum(cat_values.values())
    if total == 0:
        return {"total_value": 0, "categories": {}}

    return {
        "total_value": round(total, 2),
        "categories": {
            cat: {"value": round(v, 2), "percentage": round(v / total * 100, 2)}
            for cat, v in cat_values.items()
        },
    }


def calculate_drift(current: dict, target: dict) -> dict:
    """
    Compare current allocation percentages against target fractions.
    Returns drift analysis: action = SELL | BUY | OK per category.
    """
    current_cats = current.get("categories", {})
    drift = {}

    all_cats = set(list(current_cats.keys()) + list(target.keys()))
    for cat in all_cats:
        cur_pct = current_cats.get(cat, {}).get("percentage", 0)  # already in %
        tgt_pct = target.get(cat, 0) * 100                        # convert fraction→%
        diff    = cur_pct - tgt_pct
        drift[cat] = {
            "current_pct": round(cur_pct, 2),
            "target_pct":  round(tgt_pct, 2),
            "drift_pct":   round(diff, 2),
            "action":      "SELL" if diff > 2 else ("BUY" if diff < -2 else "OK"),
        }

    return drift


def generate_rebalancing_plan(
    holdings: List[dict],
    risk_level: str = "medium",
    target_allocation: Optional[dict] = None,
    rebalance_threshold: float = 5.0,
    min_trade_value: float = 1000.0,
    existing_fund_names: list = None,
) -> dict:
    """
    Generate specific rebalancing instructions.

    Parameters
    ----------
    holdings            : list of holding dicts (ticker, quantity, current_price, category)
    risk_level          : "low" | "medium" | "high"  (used when target_allocation is None)
    target_allocation   : override target fractions {category: fraction}
    rebalance_threshold : min drift % to trigger a rebalancing recommendation
    min_trade_value     : ignore trades smaller than this INR amount
    existing_fund_names : list of mutual fund names the user already holds.
                          BUY suggestions for each category will exclude these funds
                          to prevent "buy what you already own" conflicts.

    Returns
    -------
    dict with: needs_rebalancing, max_drift_pct, sell_orders, buy_orders, summary, …
    """
    if target_allocation is None:
        target_allocation = DEFAULT_TARGETS.get(risk_level, DEFAULT_TARGETS["medium"])

    # Build set of already-owned fund names for O(1) conflict checking
    owned_funds = set(existing_fund_names) if existing_fund_names else set()

    current   = calculate_current_allocation(holdings)
    total_val = current.get("total_value", 0)

    if total_val == 0:
        return {"error": "No portfolio value found"}

    drift = calculate_drift(current, target_allocation)
    max_drift = max((abs(d["drift_pct"]) for d in drift.values()), default=0)

    sell_orders: List[dict] = []
    buy_orders:  List[dict] = []

    for cat, info in drift.items():
        diff_value = abs(info["drift_pct"] / 100 * total_val)

        if info["action"] == "SELL" and diff_value >= min_trade_value:
            cat_holdings = [
                h for h in holdings
                if (h.get("category") or _auto_category(h.get("ticker", ""), h.get("asset_type", "stock"))) == cat
            ]
            cat_total = sum(h.get("quantity", 0) * h.get("current_price", 0) for h in cat_holdings)

            for h in cat_holdings:
                h_value = h.get("quantity", 0) * h.get("current_price", 0)
                portion = (h_value / cat_total * diff_value) if cat_total > 0 else 0
                if portion < min_trade_value:
                    continue
                price   = h.get("current_price", 1) or 1
                qty     = math.floor(portion / price)
                if qty < 1:
                    continue
                sell_orders.append({
                    "ticker":          h.get("ticker"),
                    "action":          "SELL",
                    "quantity":        qty,
                    "current_price":   price,
                    "estimated_value": round(qty * price, 2),
                    "category":        cat,
                    "holding_period":  h.get("holding_period", "unknown"),
                    "reason":          f"Overweight {cat} by {info['drift_pct']:.1f}%",
                })

        elif info["action"] == "BUY" and diff_value >= min_trade_value:
            raw_suggestions = _INSTRUMENT_SUGGESTIONS.get(cat, ["Consult advisor"])

            # Split suggestions into fresh vs already-owned
            fresh_suggestions = [s for s in raw_suggestions if s not in owned_funds]
            conflict_funds    = [s for s in raw_suggestions if s in owned_funds]

            # Prefer fresh suggestions; fall back with a note if all are owned
            if fresh_suggestions:
                final_suggestions = fresh_suggestions
                conflict_note = (
                    f"Note: {', '.join(conflict_funds)} already in your portfolio — "
                    f"top up existing SIP there instead of buying separately."
                ) if conflict_funds else None
            else:
                # Every suggestion for this category is already owned
                final_suggestions = raw_suggestions
                conflict_note = (
                    f"All standard suggestions for {cat} are already in your portfolio. "
                    f"Consider topping up existing SIPs rather than opening new ones, "
                    f"or explore alternative funds in this category."
                )

            buy_orders.append({
                "category":              cat,
                "action":                "BUY",
                "target_amount":         round(diff_value, 2),
                "reason":                f"Underweight {cat} by {abs(info['drift_pct']):.1f}%",
                "suggested_instruments": final_suggestions,
                "conflict_note":         conflict_note,
            })

    # Tax-efficient order: LTCG sells first (12.5%) before STCG (20%)
    sell_orders.sort(key=lambda x: 0 if x.get("holding_period") == "LTCG" else 1)
    buy_orders.sort(key=lambda x: x.get("target_amount", 0), reverse=True)

    return {
        "needs_rebalancing":    max_drift >= rebalance_threshold,
        "max_drift_pct":        round(max_drift, 2),
        "total_portfolio_value": round(total_val, 2),
        "current_allocation":   current,
        "target_allocation":    target_allocation,
        "drift_analysis":       drift,
        "sell_orders":          sell_orders,
        "buy_orders":           buy_orders,
        "summary": {
            "total_sell_value": round(sum(o["estimated_value"] for o in sell_orders), 2),
            "total_buy_value":  round(sum(o["target_amount"]   for o in buy_orders),  2),
            "num_sell_trades":  len(sell_orders),
            "num_buy_trades":   len(buy_orders),
        },
        "execution_notes": [
            "Execute sell orders before buy orders to free up capital",
            "Tax-efficient: LTCG (12.5%) sells are ordered before STCG (20%) sells",
            "Spread large buy orders over 2-3 days to reduce market impact",
            "Prefer index funds for large-cap allocation; diversified funds for mid-cap",
        ],
    }


def get_rebalancing_summary(holdings: List[dict], risk_level: str = "medium") -> str:
    """Plain-text summary of the rebalancing plan."""
    plan = generate_rebalancing_plan(holdings, risk_level)
    if "error" in plan:
        return plan["error"]

    lines = [
        f"Portfolio Value : INR {plan['total_portfolio_value']:,.2f}",
        f"Max Drift       : {plan['max_drift_pct']}%",
        f"Rebalancing     : {'NEEDED' if plan['needs_rebalancing'] else 'NOT NEEDED'}",
    ]

    if plan["sell_orders"]:
        lines.append("\nSELL ORDERS:")
        for o in plan["sell_orders"]:
            lines.append(
                f"  SELL {o['quantity']} x {o['ticker']} @ {o['current_price']:.2f}"
                f" = INR {o['estimated_value']:,.0f}  [{o['reason']}]"
            )

    if plan["buy_orders"]:
        lines.append("\nBUY ORDERS:")
        for o in plan["buy_orders"]:
            lines.append(f"  BUY INR {o['target_amount']:,.0f} in {o['category']}  [{o['reason']}]")
            lines.append(f"    Suggestions: {', '.join(o['suggested_instruments'][:2])}")

    return "\n".join(lines)
