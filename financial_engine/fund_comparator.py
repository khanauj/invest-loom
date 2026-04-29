"""
fund_comparator.py - Compare two or more funds for a specific goal

For each fund shows:
  - Projected corpus at goal horizon (using fund's 5yr return)
  - Total expense drag in INR
  - Net corpus after expenses
  - Wealth multiplier
  - Risk-adjusted return
  - Whether the fund hits the goal amount
  - Corpus gap vs goal

Usage:
  compare_funds(["UTI Nifty 50", "Axis Midcap", "SBI Small Cap"],
                monthly_sip=8000, years=10, goal_amount=2000000)
"""

import math
from typing import List, Optional
from .fund_database import FUNDS, search_funds, get_fund_by_id
from .sip_calculator import project_corpus, sip_needed_for_goal

# Risk penalty used for risk-adjusted return (deducted from raw CAGR)
RISK_PENALTY = {
    "very_low":    0.0,
    "low":         0.5,
    "low_medium":  1.0,
    "medium":      1.5,
    "medium_high": 2.5,
    "high":        4.0,
}


def _find_fund(query: str) -> dict:
    """Find a fund by id first, then by name search."""
    fund = get_fund_by_id(query)
    if fund:
        return fund
    results = search_funds(query)
    return results[0] if results else {}


def _expense_drag_inr(gross_corpus: float, expense_ratio_pct: float, years: int) -> float:
    """
    Approximate INR lost to expense ratio.
    Conservative estimate: ratio applied to average AUM (half of final corpus).
    """
    avg_aum = gross_corpus / 2
    return round(avg_aum * expense_ratio_pct / 100 * years * 0.5, 0)


def compare_funds(
    fund_queries: List[str],
    monthly_sip: float,
    years: int,
    goal_amount: Optional[float] = None,
    existing_corpus: float = 0.0,
    step_up_pct: float = 0.0,
) -> dict:
    """
    Compare multiple funds side-by-side for a goal.

    Parameters
    ----------
    fund_queries    : fund names, ids, or partial names to search
    monthly_sip     : monthly SIP amount in INR
    years           : investment horizon
    goal_amount     : optional target corpus in INR
    existing_corpus : existing lumpsum already invested
    step_up_pct     : annual SIP step-up percentage

    Returns
    -------
    dict with ranked results, winner, corpus differences, summary
    """
    results  = []
    not_found = []

    for query in fund_queries:
        fund = _find_fund(query)
        if not fund:
            not_found.append(query)
            continue

        cagr       = fund.get("returns_5yr", 12.0)
        projection = project_corpus(
            monthly_sip, years,
            cagr=cagr,
            step_up_pct=step_up_pct,
            existing_corpus=existing_corpus,
        )
        gross_corpus = projection["final_corpus"]
        invested     = projection["total_invested"]

        # Expense drag
        drag       = _expense_drag_inr(gross_corpus, fund.get("expense_ratio", 1.0), years)
        net_corpus = round(gross_corpus - drag)
        wealth_gain = net_corpus - invested

        # Goal analysis
        hits_goal  = (net_corpus >= goal_amount) if goal_amount else None
        goal_gap   = round(max(0, goal_amount - net_corpus)) if goal_amount else 0
        goal_surplus = round(max(0, net_corpus - goal_amount)) if goal_amount else 0

        # SIP needed (for this fund's return) to hit goal
        sip_for_goal = None
        if goal_amount:
            calc = sip_needed_for_goal(goal_amount, years, cagr=cagr,
                                       existing_corpus=existing_corpus)
            sip_for_goal = calc["monthly_sip_needed"]

        # Risk-adjusted return
        penalty        = RISK_PENALTY.get(fund.get("risk", "medium"), 1.5)
        risk_adj_return = round(cagr - penalty, 2)

        results.append({
            "fund_name":        fund["name"],
            "fund_house":       fund["fund_house"],
            "category":         fund["category"],
            "fund_type":        fund["fund_type"],
            "risk":             fund["risk"],
            "expense_ratio":    fund["expense_ratio"],
            "returns_1yr":      fund.get("returns_1yr"),
            "returns_3yr":      fund.get("returns_3yr"),
            "returns_5yr":      cagr,
            "risk_adj_return":  risk_adj_return,
            "monthly_sip":      round(monthly_sip),
            "years":            years,
            "step_up_pct":      step_up_pct,
            "total_invested":   invested,
            "gross_corpus":     gross_corpus,
            "expense_drag_inr": round(drag),
            "net_corpus":       net_corpus,
            "wealth_gain":      wealth_gain,
            "wealth_multiplier": round(net_corpus / invested, 2) if invested else 0,
            "hits_goal":        hits_goal,
            "goal_gap":         goal_gap,
            "goal_surplus":     goal_surplus,
            "sip_needed_for_goal": sip_for_goal,
            "best_for":         fund.get("best_for", ""),
        })

    if not results:
        return {
            "error":     "No funds found. Check fund names.",
            "not_found": not_found,
        }

    # Rank by net_corpus (highest first)
    results.sort(key=lambda x: x["net_corpus"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    best   = results[0]
    second = results[1] if len(results) > 1 else None

    winner_notes = [
        f"Best projected corpus: {best['fund_name']}",
        f"  Net corpus : INR {best['net_corpus']:,.0f}",
        f"  Wealth gain: INR {best['wealth_gain']:,.0f}",
        f"  Multiplier : {best['wealth_multiplier']}x",
    ]
    if second:
        diff = best["net_corpus"] - second["net_corpus"]
        winner_notes.append(
            f"  vs #{2} {second['fund_name']}: INR {diff:,.0f} more corpus"
        )
    if goal_amount and not best["hits_goal"]:
        winner_notes.append(
            f"  WARNING: Even the best fund misses the goal by INR {best['goal_gap']:,.0f}"
        )

    return {
        "monthly_sip":    round(monthly_sip),
        "years":          years,
        "goal_amount":    goal_amount,
        "step_up_pct":    step_up_pct,
        "existing_corpus": round(existing_corpus),
        "funds_compared": len(results),
        "not_found":      not_found,
        "results":        results,
        "winner":         best["fund_name"],
        "winner_notes":   winner_notes,
        "summary": (
            f"Compared {len(results)} fund(s) | "
            f"INR {monthly_sip:,.0f}/mo for {years}yr"
            + (f" | Goal: INR {goal_amount:,.0f}" if goal_amount else "")
            + f" | Best: {best['fund_name']} → INR {best['net_corpus']:,.0f}"
        ),
    }
