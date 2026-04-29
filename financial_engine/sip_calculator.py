"""
sip_calculator.py - SIP mathematics and corpus projection engine

Answers:
  1. "INR 8,000/mo for 10 years at 12% CAGR = INR X"          → project_corpus()
  2. "How long until I reach INR 20L at INR 8,000/mo?"         → months_to_goal()
  3. "How much SIP do I need to reach INR 20L in 10 years?"    → sip_needed_for_goal()
  4. Year-by-year growth table with wealth gain                 → project_corpus() yearly_table
  5. Step-up SIP projection (SIP increases % each year)        → project_corpus(step_up_pct=10)
"""

import math
from typing import Optional

# Default CAGR assumptions by strategy
STRATEGY_RETURNS = {
    "liquid":     6.5,
    "debt":       7.2,
    "hybrid":    10.5,
    "equity":    12.0,
    "aggressive": 15.0,
}

# Strategy selected by investment horizon (years)
HORIZON_TO_STRATEGY = [
    (2,  "liquid"),
    (3,  "debt"),
    (5,  "hybrid"),
    (10, "equity"),
    (99, "aggressive"),
]

RISK_CAGR_ADJUST = {"low": -1.5, "medium": 0.0, "high": +1.5}


def _default_cagr(years: int, risk_level: str = "medium") -> float:
    """Return a sensible default CAGR based on horizon and risk level."""
    strategy = "aggressive"
    for threshold, s in HORIZON_TO_STRATEGY:
        if years <= threshold:
            strategy = s
            break
    base   = STRATEGY_RETURNS[strategy]
    adjust = RISK_CAGR_ADJUST.get(risk_level, 0.0)
    return round(base + adjust, 1)


# ── Core formula helpers ───────────────────────────────────────────────────────

def _fv_sip(monthly_sip: float, monthly_rate: float, months: int) -> float:
    """Standard SIP future-value formula: FV = P×[((1+r)^n − 1)/r]×(1+r)."""
    if monthly_rate == 0:
        return monthly_sip * months
    return monthly_sip * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)


def _lumpsum_fv(principal: float, monthly_rate: float, months: int) -> float:
    """Future value of a lumpsum invested today."""
    return principal * (1 + monthly_rate) ** months


# ── Public API ─────────────────────────────────────────────────────────────────

def project_corpus(
    monthly_sip: float,
    years: int,
    cagr: Optional[float] = None,
    risk_level: str = "medium",
    step_up_pct: float = 0.0,
    existing_corpus: float = 0.0,
) -> dict:
    """
    Project final corpus from a monthly SIP.

    Parameters
    ----------
    monthly_sip     : INR amount invested each month
    years           : investment horizon in years
    cagr            : annual return % (auto-selected if None)
    risk_level      : low / medium / high (used for auto CAGR)
    step_up_pct     : SIP increases by this % every year (e.g. 10 = 10% step-up)
    existing_corpus : lumpsum already invested (grows alongside SIP)

    Returns
    -------
    dict with final_corpus, total_invested, wealth_gain, year-by-year table, summary line
    """
    if cagr is None:
        cagr = _default_cagr(years, risk_level)

    monthly_rate = cagr / 100 / 12
    yearly_table = []
    sip          = float(monthly_sip)
    corpus       = float(existing_corpus)
    total_invested = float(existing_corpus)

    for yr in range(1, years + 1):
        for _ in range(12):
            corpus = corpus * (1 + monthly_rate) + sip
            total_invested += sip
        yearly_table.append({
            "year":           yr,
            "monthly_sip":    round(sip),
            "total_invested": round(total_invested),
            "corpus":         round(corpus),
            "wealth_gain":    round(corpus - total_invested),
            "multiplier":     round(corpus / total_invested, 2) if total_invested else 0,
        })
        if step_up_pct > 0:
            sip = sip * (1 + step_up_pct / 100)

    final_corpus   = round(corpus)
    total_invested = round(total_invested)
    wealth_gain    = final_corpus - total_invested

    return {
        "monthly_sip":      round(monthly_sip),
        "years":            years,
        "cagr_pct":         cagr,
        "step_up_pct":      step_up_pct,
        "existing_corpus":  round(existing_corpus),
        "total_invested":   total_invested,
        "final_corpus":     final_corpus,
        "wealth_gain":      wealth_gain,
        "wealth_multiplier": round(final_corpus / total_invested, 2) if total_invested else 0,
        "yearly_table":     yearly_table,
        "summary": (
            f"INR {monthly_sip:,.0f}/mo"
            + (f" (step-up {step_up_pct}%/yr)" if step_up_pct else "")
            + f" for {years} years at {cagr}% CAGR"
            + (f" + INR {existing_corpus:,.0f} lumpsum" if existing_corpus else "")
            + f" = INR {final_corpus:,.0f}"
            + f"  (invested INR {total_invested:,.0f}, gain INR {wealth_gain:,.0f})"
        ),
    }


def months_to_goal(
    target_amount: float,
    monthly_sip: float,
    cagr: float,
    existing_corpus: float = 0.0,
) -> dict:
    """
    How many months/years of SIP needed to reach target_amount?

    Uses logarithmic formula; iterates when existing_corpus > 0.
    """
    monthly_rate = cagr / 100 / 12

    if existing_corpus >= target_amount:
        return {
            "target_amount":   round(target_amount),
            "monthly_sip":     round(monthly_sip),
            "cagr_pct":        cagr,
            "months_needed":   0,
            "years_needed":    0,
            "extra_months":    0,
            "total_invested":  0,
            "wealth_gain":     round(target_amount - existing_corpus),
            "summary":         "Goal already reached with existing corpus.",
        }

    if existing_corpus > 0:
        # Iterate month by month (existing lumpsum + SIP)
        corpus = float(existing_corpus)
        invested = 0.0
        months = 0
        while corpus < target_amount and months < 600:
            corpus = corpus * (1 + monthly_rate) + monthly_sip
            invested += monthly_sip
            months += 1
    else:
        if monthly_rate == 0:
            months = math.ceil(target_amount / monthly_sip)
        else:
            val = 1 + (target_amount * monthly_rate) / (monthly_sip * (1 + monthly_rate))
            if val <= 1:
                months = 1
            else:
                months = math.ceil(math.log(val) / math.log(1 + monthly_rate))
        invested = monthly_sip * months

    years      = months // 12
    rem_months = months % 12
    invested   = round(monthly_sip * months)

    return {
        "target_amount":  round(target_amount),
        "monthly_sip":    round(monthly_sip),
        "cagr_pct":       cagr,
        "existing_corpus": round(existing_corpus),
        "months_needed":  months,
        "years_needed":   years,
        "extra_months":   rem_months,
        "total_invested": invested,
        "wealth_gain":    round(target_amount - invested),
        "summary": (
            f"At INR {monthly_sip:,.0f}/mo and {cagr}% CAGR, "
            f"you reach INR {target_amount:,.0f} in "
            f"{years} years {rem_months} months "
            f"(total invested: INR {invested:,.0f})"
        ),
    }


def sip_needed_for_goal(
    target_amount: float,
    years: int,
    cagr: Optional[float] = None,
    risk_level: str = "medium",
    existing_corpus: float = 0.0,
) -> dict:
    """
    Monthly SIP amount needed to reach target in given years.

    If existing_corpus provided, calculates only the top-up SIP needed.
    """
    if cagr is None:
        cagr = _default_cagr(years, risk_level)

    monthly_rate = cagr / 100 / 12
    months       = years * 12

    # Future value of existing corpus
    existing_fv = _lumpsum_fv(existing_corpus, monthly_rate, months) if existing_corpus else 0.0
    remaining   = max(0.0, target_amount - existing_fv)

    if remaining == 0:
        return {
            "target_amount":    round(target_amount),
            "years":            years,
            "cagr_pct":         cagr,
            "monthly_sip_needed": 0,
            "existing_corpus":  round(existing_corpus),
            "existing_fv":      round(existing_fv),
            "total_invested":   0,
            "wealth_gain":      round(target_amount - existing_corpus),
            "summary":          "No additional SIP needed — existing corpus already covers the goal.",
        }

    if monthly_rate == 0:
        sip = math.ceil(remaining / months)
    else:
        sip = math.ceil(
            remaining / ((((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate))
        )

    invested = sip * months

    return {
        "target_amount":      round(target_amount),
        "years":              years,
        "cagr_pct":           cagr,
        "existing_corpus":    round(existing_corpus),
        "existing_fv":        round(existing_fv),
        "monthly_sip_needed": sip,
        "total_invested":     round(invested),
        "wealth_gain":        round(target_amount - invested - existing_corpus),
        "summary": (
            f"To reach INR {target_amount:,.0f} in {years} years at {cagr}% CAGR"
            + (f" (existing INR {existing_corpus:,.0f} → grows to INR {existing_fv:,.0f})" if existing_corpus else "")
            + f" → invest INR {sip:,.0f}/mo"
            + f"  (total: INR {invested:,.0f}, gain: INR {target_amount - invested:,.0f})"
        ),
    }


def compare_flat_vs_stepup(
    monthly_sip: float,
    years: int,
    cagr: float,
    step_up_pct: float = 10.0,
) -> dict:
    """Compare flat SIP vs step-up SIP side by side."""
    flat   = project_corpus(monthly_sip, years, cagr=cagr, step_up_pct=0.0)
    stepup = project_corpus(monthly_sip, years, cagr=cagr, step_up_pct=step_up_pct)

    extra_corpus   = stepup["final_corpus"]   - flat["final_corpus"]
    extra_invested = stepup["total_invested"] - flat["total_invested"]

    return {
        "flat_sip":          flat,
        "step_up_sip":       stepup,
        "step_up_pct":       step_up_pct,
        "extra_corpus":      extra_corpus,
        "extra_invested":    extra_invested,
        "extra_wealth_gain": extra_corpus - extra_invested,
        "summary": (
            f"Step-up {step_up_pct}% gives INR {extra_corpus:,.0f} more corpus "
            f"by investing INR {extra_invested:,.0f} more over {years} years"
        ),
    }
