"""
sip_advisor.py - Unified SIP advisory engine

Combines sip_calculator + fund_allocator + fund_comparator into
one complete answer:

  "Put INR 8,000/mo SIP into these specific funds:
     INR 2,800 → UTI Nifty 50 Index Fund
     INR 1,600 → Axis Midcap Fund
     INR  800  → SBI Small Cap Fund
     INR 1,600 → HDFC Short Duration Fund
     INR  800  → Nippon India Gold ETF
     INR  400  → Motilal Oswal Nasdaq 100 FOF

   Projected corpus in 10 years: INR 18,64,320
   With 10% step-up each year  : INR 29,41,850
   To reach INR 25L goal       : you need INR 10,750/mo
                                  or step up to reach it by year 12"
"""

from typing import Optional, List
from .sip_calculator  import project_corpus, sip_needed_for_goal, months_to_goal, compare_flat_vs_stepup
from .fund_allocator  import allocate_sip
from .fund_comparator import compare_funds


def full_sip_plan(
    monthly_sip: float,
    goal_type: str      = "wealth",
    goal_amount: float  = None,
    horizon_years: int  = 10,
    risk_level: str     = "medium",
    step_up_pct: float  = 10.0,
    existing_corpus: float = 0.0,
    prefer_low_cost: bool  = False,
    existing_sip_funds: list = None,
) -> dict:
    """
    Complete SIP plan answering all 5 user questions:

    1. Which specific fund gets how much SIP (INR + %)
    2. Projected corpus (flat SIP and with step-up)
    3. SIP duration to reach goal_amount
    4. Monthly SIP needed to reach goal_amount
    5. Fund-level corpus projections

    Parameters
    ----------
    monthly_sip     : Current/planned monthly SIP in INR
    goal_type       : wealth / education / retirement / house / wedding /
                      emergency_fund / tax_saving / vacation
    goal_amount     : Target corpus in INR (optional)
    horizon_years   : Investment horizon in years
    risk_level      : low / medium / high
    step_up_pct     : Annual SIP increase % (default 10%)
    existing_corpus : Already-invested lumpsum in INR
    prefer_low_cost : Prefer index/passive funds (lower expense ratio)

    Returns
    -------
    Complete plan dict with all projections, fund splits, goal analysis
    """
    # 1. Fund allocation
    allocation   = allocate_sip(
        total_sip          = monthly_sip,
        risk_level         = risk_level,
        goal_type          = goal_type,
        horizon_years      = horizon_years,
        prefer_low_cost    = prefer_low_cost,
        existing_sip_funds = existing_sip_funds,
    )
    blended_cagr = allocation["blended_return"]

    # 2. Corpus projections
    flat_proj   = project_corpus(monthly_sip, horizon_years,
                                 cagr=blended_cagr, step_up_pct=0.0,
                                 existing_corpus=existing_corpus)
    stepup_proj = project_corpus(monthly_sip, horizon_years,
                                 cagr=blended_cagr, step_up_pct=step_up_pct,
                                 existing_corpus=existing_corpus)
    stepup_comparison = compare_flat_vs_stepup(monthly_sip, horizon_years,
                                               cagr=blended_cagr, step_up_pct=step_up_pct)

    # 3 & 4. Goal analysis
    goal_analysis = None
    if goal_amount:
        sip_calc   = sip_needed_for_goal(goal_amount, horizon_years,
                                         cagr=blended_cagr,
                                         existing_corpus=existing_corpus)
        duration   = months_to_goal(goal_amount, monthly_sip,
                                    cagr=blended_cagr,
                                    existing_corpus=existing_corpus)
        stepup_dur = months_to_goal(goal_amount, monthly_sip,
                                    cagr=blended_cagr * 1.02,   # ~2% boost from step-up
                                    existing_corpus=existing_corpus)

        flat_reaches_goal   = flat_proj["final_corpus"]   >= goal_amount
        stepup_reaches_goal = stepup_proj["final_corpus"] >= goal_amount
        shortfall_flat      = max(0, goal_amount - flat_proj["final_corpus"])
        shortfall_stepup    = max(0, goal_amount - stepup_proj["final_corpus"])

        goal_analysis = {
            "goal_amount":            round(goal_amount),
            "flat_final_corpus":      flat_proj["final_corpus"],
            "flat_reaches_goal":      flat_reaches_goal,
            "flat_shortfall":         round(shortfall_flat),
            "stepup_final_corpus":    stepup_proj["final_corpus"],
            "stepup_reaches_goal":    stepup_reaches_goal,
            "stepup_shortfall":       round(shortfall_stepup),
            "sip_needed":             sip_calc["monthly_sip_needed"],
            "extra_sip_needed":       max(0, sip_calc["monthly_sip_needed"] - round(monthly_sip)),
            "months_at_current_sip":  duration["months_needed"],
            "years_at_current_sip":   duration["years_needed"],
            "extra_months":           duration["extra_months"],
            "months_with_stepup":     stepup_dur["months_needed"],
            "verdict": (
                "Goal reached with flat SIP" if flat_reaches_goal
                else "Goal reached with step-up SIP" if stepup_reaches_goal
                else f"Increase SIP by INR {max(0, sip_calc['monthly_sip_needed'] - round(monthly_sip)):,.0f}/mo to reach goal on time"
            ),
        }

    # 5. Per-fund corpus projections
    fund_projections = []
    for alloc in allocation["allocations"]:
        proj = project_corpus(
            alloc["sip_amount"], horizon_years,
            cagr          = alloc["returns_5yr"],
            step_up_pct   = step_up_pct,
        )
        fund_projections.append({
            "fund_name":     alloc["fund_name"],
            "category":      alloc["category"],
            "sip_amount":    alloc["sip_amount"],
            "percentage":    alloc["percentage"],
            "returns_5yr":   alloc["returns_5yr"],
            "final_corpus":  proj["final_corpus"],
            "total_invested":proj["total_invested"],
            "wealth_gain":   proj["wealth_gain"],
        })
    fund_projections.sort(key=lambda x: x["final_corpus"], reverse=True)

    total_projected = sum(p["final_corpus"] for p in fund_projections)

    return {
        "input": {
            "monthly_sip":      round(monthly_sip),
            "goal_type":        goal_type,
            "goal_amount":      round(goal_amount) if goal_amount else None,
            "horizon_years":    horizon_years,
            "risk_level":       risk_level,
            "step_up_pct":      step_up_pct,
            "existing_corpus":  round(existing_corpus),
        },
        "fund_allocation":      allocation["allocations"],
        "blended_cagr":         blended_cagr,
        "flat_projection":      flat_proj,
        "stepup_projection":    stepup_proj,
        "stepup_comparison":    stepup_comparison,
        "fund_level_projections": fund_projections,
        "total_projected_corpus": total_projected,
        "goal_analysis":        goal_analysis,
    }


def quick_corpus(monthly_sip: float, years: int,
                 cagr: float = 12.0, step_up_pct: float = 0.0) -> str:
    """One-liner: 'INR 8,000/mo for 10 years at 12% = INR X'"""
    p = project_corpus(monthly_sip, years, cagr=cagr, step_up_pct=step_up_pct)
    return p["summary"]


def quick_sip_needed(target: float, years: int,
                     cagr: float = 12.0) -> str:
    """One-liner: 'Need INR X/mo to reach INR Y in Z years'"""
    p = sip_needed_for_goal(target, years, cagr=cagr)
    return p["summary"]
