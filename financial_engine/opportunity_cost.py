"""
opportunity_cost.py - Opportunity Cost Engine (Behavioral Nudging)

Shows users what they LOSE by not following the recommendation.
Uses compound interest and real financial math to quantify inaction.

Example output:
  "If you don't increase SIP by INR 2,000/mo now,
   you lose INR 5,47,000 over 10 years at 12% returns."
"""

# Expected annual returns by instrument type
RETURNS = {
    "equity": 0.12,      # 12% long-term equity
    "debt": 0.07,        # 7% debt funds
    "sip": 0.12,         # 12% SIP in equity MF
    "savings": 0.04,     # 4% savings account (inflation-adjusted = ~0%)
    "inflation": 0.06,   # 6% inflation
}


def _future_value_lumpsum(principal, rate, years):
    """FV = P × (1 + r)^n"""
    return int(principal * (1 + rate) ** years)


def _future_value_sip(monthly, rate, years):
    """FV of monthly SIP: M × [((1+r)^n - 1) / r] × (1+r), where r = monthly rate"""
    if monthly <= 0 or years <= 0:
        return 0
    r = rate / 12
    n = years * 12
    return int(monthly * (((1 + r) ** n - 1) / r) * (1 + r))


def compute_opportunity_cost(action, profile, intensity_metrics):
    """
    Compute the opportunity cost of NOT following the recommended action.

    Args:
        action: The recommended action string
        profile: Dict of user's financial inputs
        intensity_metrics: Dict from compute_intensity()

    Returns dict with:
        cost_of_inaction: str  (human-readable)
        gain_if_acted: str     (human-readable)
        numbers: dict          (raw computed values)
        nudge: str             (behavioral nudge message)
    """
    salary = profile.get("salary", 0)
    savings = profile.get("monthly_savings", 0)
    goal_years = profile.get("goal_years", 5)
    sip_amount = profile.get("sip_amount", 0)
    sip_active = profile.get("sip_active", False)
    equity_val = profile.get("current_equity_value", 0)
    debt_val = profile.get("current_debt_value", 0)
    emergency_months = profile.get("emergency_fund_months", 0)
    dependents = profile.get("dependents", 0)

    if action == "INCREASE_SIP":
        increase = intensity_metrics.get("recommended_increase", 2000)
        new_sip = intensity_metrics.get("new_sip", sip_amount + increase)

        gain_with = _future_value_sip(new_sip, RETURNS["sip"], goal_years)
        gain_without = _future_value_sip(sip_amount, RETURNS["sip"], goal_years)
        lost = gain_with - gain_without

        return {
            "cost_of_inaction": f"You lose INR {lost:,} over {goal_years} years by not increasing SIP",
            "gain_if_acted": f"Increasing SIP by INR {increase:,}/mo grows to INR {gain_with:,} (vs INR {gain_without:,} now)",
            "numbers": {
                "future_value_current_sip": gain_without,
                "future_value_new_sip": gain_with,
                "opportunity_loss": lost,
                "years": goal_years,
                "assumed_return": "12% p.a.",
            },
            "nudge": f"Just INR {increase:,}/mo more today = INR {lost:,} more at goal. That's INR {int(lost/goal_years):,}/year you're leaving on the table.",
        }

    elif action == "START_SIP":
        recommended = intensity_metrics.get("recommended_sip", 5000)

        gain = _future_value_sip(recommended, RETURNS["sip"], goal_years)
        idle = _future_value_sip(recommended, RETURNS["savings"], goal_years)
        lost = gain - idle

        return {
            "cost_of_inaction": f"Keeping INR {recommended:,}/mo idle loses INR {lost:,} vs SIP over {goal_years} years",
            "gain_if_acted": f"SIP of INR {recommended:,}/mo at 12% grows to INR {gain:,} (vs INR {idle:,} in savings)",
            "numbers": {
                "future_value_sip": gain,
                "future_value_idle": idle,
                "opportunity_loss": lost,
                "years": goal_years,
                "assumed_return_sip": "12% p.a.",
                "assumed_return_idle": "4% p.a.",
            },
            "nudge": f"Starting a SIP of INR {recommended:,}/mo today could earn you INR {lost:,} more than a savings account. Every month you delay costs INR {int(lost / (goal_years * 12)):,}.",
        }

    elif action == "STOP_SIP":
        freed = intensity_metrics.get("freed_amount", sip_amount)
        # Cost of continuing an unaffordable SIP = potential debt/emergency shortfall
        emergency_gap = max(0, (salary - savings) * 3 - (salary - savings) * emergency_months)

        return {
            "cost_of_inaction": f"Continuing SIP drains INR {freed:,}/mo from an already stretched budget",
            "gain_if_acted": f"Freeing INR {freed:,}/mo builds INR {freed * 12:,}/year safety buffer",
            "numbers": {
                "monthly_freed": freed,
                "annual_freed": freed * 12,
                "emergency_gap": emergency_gap,
            },
            "nudge": f"Stopping SIP now frees INR {freed:,}/mo. In {max(1, int(emergency_gap / freed)) if freed > 0 else '?'} months, you'll have a proper emergency fund. Safety first, SIP later.",
        }

    elif action == "REDUCE_SIP":
        reduction = intensity_metrics.get("recommended_reduction", 2000)
        new_sip = intensity_metrics.get("new_sip", sip_amount - reduction)

        return {
            "cost_of_inaction": f"Over-committing INR {sip_amount:,}/mo to SIP risks missing bills or taking debt",
            "gain_if_acted": f"Reducing to INR {new_sip:,}/mo saves INR {reduction * 12:,}/year for essentials while SIP continues",
            "numbers": {
                "current_sip": sip_amount,
                "new_sip": new_sip,
                "monthly_freed": reduction,
                "annual_freed": reduction * 12,
            },
            "nudge": f"A smaller SIP of INR {new_sip:,}/mo still compounds to INR {_future_value_sip(new_sip, RETURNS['sip'], goal_years):,} over {goal_years} years. But INR {reduction:,}/mo freed keeps your family safe TODAY.",
        }

    elif action == "SELL":
        sell_amount = intensity_metrics.get("sell_amount", int(equity_val * 0.3))
        remaining = intensity_metrics.get("remaining_equity", equity_val - sell_amount)
        # Risk of NOT selling: potential loss in 1yr volatile market
        potential_loss = int(equity_val * 0.15)  # 15% downside risk

        return {
            "cost_of_inaction": f"Not selling risks a potential INR {potential_loss:,} loss if market drops 15% before your goal",
            "gain_if_acted": f"Selling INR {sell_amount:,} now locks in gains with {goal_years}yr left — secure your goal",
            "numbers": {
                "sell_amount": sell_amount,
                "potential_downside": potential_loss,
                "secured_amount": sell_amount,
                "remaining_equity": remaining,
            },
            "nudge": f"Your goal is {goal_years} year(s) away. Markets can drop 15-20% in a year. Selling INR {sell_amount:,} now means your goal is funded regardless of what markets do.",
        }

    elif action == "REBALANCE":
        shift = intensity_metrics.get("shift_amount", 0)
        current_pct = intensity_metrics.get("current_equity_pct", 0)
        target_pct = intensity_metrics.get("target_equity_pct", 60)
        excess_equity = int(equity_val * (current_pct - target_pct) / 100) if current_pct > target_pct else 0
        risk_amount = int(excess_equity * 0.20)  # 20% downside on excess

        return {
            "cost_of_inaction": f"INR {excess_equity:,} excess equity exposed to INR {risk_amount:,} potential drawdown",
            "gain_if_acted": f"Moving INR {shift:,} to debt protects against volatility while earning 7% safely",
            "numbers": {
                "excess_equity": excess_equity,
                "potential_drawdown": risk_amount,
                "shift_amount": shift,
                "safe_return": "7% p.a. in debt",
            },
            "nudge": f"You're {current_pct:.0f}% in equity — that's {current_pct - target_pct:.0f}% more than ideal. Shifting INR {shift:,} to debt protects INR {risk_amount:,} from a market crash.",
        }

    elif action == "EMERGENCY_FUND_BUILD":
        gap = intensity_metrics.get("gap", 0)
        monthly_alloc = intensity_metrics.get("monthly_allocation", 2500)
        months = intensity_metrics.get("months_to_target", 0)
        # Cost of not having emergency fund
        monthly_expenses = salary - savings
        crisis_cost = monthly_expenses * 3  # 3-month crisis scenario

        return {
            "cost_of_inaction": f"Without emergency fund, a 3-month crisis costs INR {crisis_cost:,} — likely funded by high-interest debt",
            "gain_if_acted": f"Saving INR {monthly_alloc:,}/mo fills the INR {gap:,} gap in ~{months} months — total protection",
            "numbers": {
                "crisis_scenario_cost": crisis_cost,
                "high_interest_debt_cost": int(crisis_cost * 0.18),  # 18% credit card interest
                "gap": gap,
                "monthly_allocation": monthly_alloc,
                "months_to_safety": months,
            },
            "nudge": f"A job loss or medical emergency without a fund means INR {crisis_cost:,} on credit cards at 18% interest = INR {int(crisis_cost * 0.18):,}/year in interest alone. INR {monthly_alloc:,}/mo now prevents that.",
        }

    elif action == "SWITCH_TO_DEBT":
        shift = intensity_metrics.get("shift_amount", 0)
        equity_risk = int(shift * 0.20)  # 20% downside

        return {
            "cost_of_inaction": f"Keeping INR {shift:,} in equity with {goal_years}yr horizon risks INR {equity_risk:,} loss",
            "gain_if_acted": f"Debt funds earn ~7% safely vs equity's 20% downside risk over short horizon",
            "numbers": {
                "shift_amount": shift,
                "equity_downside_risk": equity_risk,
                "debt_safe_return": _future_value_lumpsum(shift, RETURNS["debt"], goal_years) - shift,
            },
            "nudge": f"With only {goal_years} years left, equity can lose 20%. Moving INR {shift:,} to debt earns INR {_future_value_lumpsum(shift, RETURNS['debt'], goal_years) - shift:,} safely instead.",
        }

    elif action == "SWITCH_TO_EQUITY":
        shift = intensity_metrics.get("shift_amount", 0)
        equity_gain = _future_value_lumpsum(shift, RETURNS["equity"], goal_years) - shift
        debt_gain = _future_value_lumpsum(shift, RETURNS["debt"], goal_years) - shift
        lost = equity_gain - debt_gain

        return {
            "cost_of_inaction": f"Keeping INR {shift:,} in debt instead of equity loses INR {lost:,} over {goal_years} years",
            "gain_if_acted": f"Equity returns INR {equity_gain:,} vs debt's INR {debt_gain:,} on INR {shift:,}",
            "numbers": {
                "equity_gain": equity_gain,
                "debt_gain": debt_gain,
                "opportunity_loss": lost,
                "years": goal_years,
            },
            "nudge": f"With {goal_years} years, your INR {shift:,} earns INR {lost:,} more in equity than debt. Time is on your side — use it.",
        }

    elif action == "DIVERSIFY_PORTFOLIO":
        portfolio_total = equity_val + debt_val
        concentration_risk = int(portfolio_total * 0.15)  # 15% concentrated portfolio risk

        return {
            "cost_of_inaction": f"Concentrated portfolio risks INR {concentration_risk:,} if one sector crashes",
            "gain_if_acted": f"Diversifying reduces risk by 30-40% while maintaining similar returns",
            "numbers": {
                "portfolio_total": portfolio_total,
                "concentration_risk": concentration_risk,
                "risk_reduction": "30-40%",
            },
            "nudge": f"Only {profile.get('num_stocks', 0) + profile.get('num_mutual_funds', 0)} instruments holding INR {portfolio_total:,}. One bad bet could cost INR {concentration_risk:,}. Spreading across 5+ instruments cuts that risk in half.",
        }

    elif action == "CONTINUE_SIP":
        projected = _future_value_sip(sip_amount, RETURNS["sip"], goal_years)
        if_stopped = _future_value_lumpsum(sip_amount * 12, RETURNS["savings"], goal_years)

        return {
            "cost_of_inaction": f"Stopping SIP now loses INR {projected - if_stopped:,} in compounding over {goal_years} years",
            "gain_if_acted": f"Continuing INR {sip_amount:,}/mo SIP grows to INR {projected:,}",
            "numbers": {
                "projected_sip_value": projected,
                "if_stopped_value": if_stopped,
                "compounding_benefit": projected - if_stopped,
            },
            "nudge": f"Your discipline is worth INR {projected:,}. Stopping now means losing INR {projected - if_stopped:,} in compounding. Keep going!",
        }

    else:  # HOLD, BUY, etc.
        return {
            "cost_of_inaction": "No significant opportunity cost — current strategy is sound",
            "gain_if_acted": "Maintaining current positions preserves your gains",
            "numbers": {},
            "nudge": "You're on track. Stay consistent and review quarterly.",
        }
