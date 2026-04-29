"""
rule_engine.py - Pure IF-ELSE Financial Decision Engine (v2)

Context-aware: understands existing holdings, SIP activity, and diversification.
Zero ML dependencies. Can be deployed anywhere.

Usage:
    from financial_engine.rule_engine import predict, run_rule_engine

    result = predict(
        salary=50000, monthly_savings=15000, goal_years=8,
        risk_level="medium", dependents=2,
        investment_experience="intermediate",
        emergency_fund_months=6, debt_to_income=0.25,
        current_equity_value=100000, current_debt_value=50000,
        sip_amount=5000, sip_active=True,
        num_stocks=4, num_mutual_funds=3,
    )
"""


VALID_RISK_LEVELS = ("low", "medium", "high")
VALID_EXPERIENCE = ("beginner", "intermediate", "expert")

ACTION_DESCRIPTIONS = {
    "BUY":                   "Buy equities — strong entry point for growth.",
    "SELL":                  "Sell holdings — goal is near, lock in gains.",
    "HOLD":                  "Hold current positions — no action needed.",
    "START_SIP":             "Start a Systematic Investment Plan for long-term wealth building.",
    "STOP_SIP":              "Stop SIP — savings too low to sustain regular investments.",
    "INCREASE_SIP":          "Increase SIP amount — strong savings support higher contributions.",
    "REDUCE_SIP":            "Reduce SIP amount — current SIP is too aggressive for your situation.",
    "CONTINUE_SIP":          "Continue current SIP — on track, maintain discipline.",
    "REBALANCE":             "Rebalance portfolio — equity allocation is too high.",
    "SWITCH_TO_DEBT":        "Switch to debt instruments — lower risk for short horizon.",
    "SWITCH_TO_EQUITY":      "Switch to equity — long horizon supports higher risk.",
    "DIVERSIFY_PORTFOLIO":   "Diversify across asset classes — reduce concentration risk.",
    "EMERGENCY_FUND_BUILD":  "Build emergency fund first — insufficient safety net.",
}


def validate_inputs(salary, monthly_savings, goal_years, risk_level,
                    dependents, investment_experience, emergency_fund_months,
                    debt_to_income, current_equity_value, current_debt_value,
                    sip_amount, sip_active, num_stocks, num_mutual_funds,
                    income_type="salaried"):
    """Validate all inputs and raise ValueError with clear messages."""
    errors = []
    if not (5000 <= salary <= 500000):
        errors.append(f"salary must be 5000-500000, got {salary}")
    if not (500 <= monthly_savings <= 200000):
        errors.append(f"monthly_savings must be 500-200000, got {monthly_savings}")
    if not (1 <= goal_years <= 15):
        errors.append(f"goal_years must be 1-15, got {goal_years}")
    if risk_level not in VALID_RISK_LEVELS:
        errors.append(f"risk_level must be one of {VALID_RISK_LEVELS}, got '{risk_level}'")
    if not (0 <= dependents <= 5):
        errors.append(f"dependents must be 0-5, got {dependents}")
    if investment_experience not in VALID_EXPERIENCE:
        errors.append(f"investment_experience must be one of {VALID_EXPERIENCE}, got '{investment_experience}'")
    if not (0 <= emergency_fund_months <= 12):
        errors.append(f"emergency_fund_months must be 0-12, got {emergency_fund_months}")
    if not (0 <= debt_to_income <= 0.6):
        errors.append(f"debt_to_income must be 0.0-0.6, got {debt_to_income}")
    if not (0 <= current_equity_value <= 5000000):
        errors.append(f"current_equity_value must be 0-5000000, got {current_equity_value}")
    if not (0 <= current_debt_value <= 5000000):
        errors.append(f"current_debt_value must be 0-5000000, got {current_debt_value}")
    if not (0 <= sip_amount <= 25000):
        errors.append(f"sip_amount must be 0-25000, got {sip_amount}")
    if not isinstance(sip_active, bool):
        errors.append(f"sip_active must be True/False, got {sip_active}")
    if not (0 <= num_stocks <= 20):
        errors.append(f"num_stocks must be 0-20, got {num_stocks}")
    if not (0 <= num_mutual_funds <= 15):
        errors.append(f"num_mutual_funds must be 0-15, got {num_mutual_funds}")
    if errors:
        raise ValueError("Invalid inputs:\n  " + "\n  ".join(errors))


def _compute_confidence(action, salary, monthly_savings, goal_years, risk_level,
                        dependents, emergency_fund_months, debt_to_income,
                        equity_pct, sip_active, sip_ratio, diversification_score,
                        portfolio_total):
    """
    Compute a confidence score (0-100) for the predicted action.
    Higher score = more supporting factors align with the recommendation.
    """
    score = 60  # base confidence for matching the primary rule

    if action == "REBALANCE":
        if equity_pct > 90:
            score += 15
        if equity_pct > 85:
            score += 10
        if risk_level in ("low", "medium"):
            score += 8
        if goal_years < 5:
            score += 7

    elif action == "SELL":
        if goal_years == 1:
            score += 20
        if equity_pct > 50:
            score += 8
        if dependents >= 2:
            score += 7
        if risk_level == "low":
            score += 5

    elif action == "EMERGENCY_FUND_BUILD":
        if emergency_fund_months == 0:
            score += 20
        elif emergency_fund_months == 1:
            score += 12
        if dependents >= 3:
            score += 8
        if debt_to_income > 0.3:
            score += 5
        if monthly_savings < 5000:
            score += 5

    elif action == "STOP_SIP":
        if monthly_savings < 2500:
            score += 15
        if debt_to_income > 0.4:
            score += 10
        if dependents >= 3:
            score += 8
        if emergency_fund_months < 3:
            score += 7

    elif action == "INCREASE_SIP":
        if monthly_savings > 20000:
            score += 12
        if goal_years > 8:
            score += 8
        if debt_to_income < 0.2:
            score += 7
        if emergency_fund_months >= 6:
            score += 7
        if risk_level == "high":
            score += 6

    elif action == "REDUCE_SIP":
        if sip_ratio > 0.4:
            score += 15
        if dependents >= 4:
            score += 10
        if monthly_savings < 5000:
            score += 8
        if debt_to_income > 0.3:
            score += 7

    elif action == "CONTINUE_SIP":
        if 0.05 <= sip_ratio <= 0.25:
            score += 10
        if emergency_fund_months >= 4:
            score += 8
        if debt_to_income < 0.3:
            score += 7
        if goal_years > 5:
            score += 7
        if diversification_score >= 5:
            score += 5

    elif action == "START_SIP":
        if monthly_savings > 15000:
            score += 12
        if goal_years > 8:
            score += 8
        if emergency_fund_months >= 4:
            score += 7
        if debt_to_income < 0.2:
            score += 7
        if risk_level in ("medium", "high"):
            score += 6

    elif action == "BUY":
        if equity_pct < 20:
            score += 12
        if risk_level == "high":
            score += 10
        if goal_years > 5:
            score += 8
        if monthly_savings > 10000:
            score += 7
        if emergency_fund_months >= 6:
            score += 5

    elif action == "SWITCH_TO_DEBT":
        if equity_pct > 70:
            score += 12
        if goal_years <= 3:
            score += 10
        if risk_level == "low":
            score += 8
        if dependents >= 2:
            score += 5

    elif action == "SWITCH_TO_EQUITY":
        if goal_years > 10:
            score += 12
        if risk_level == "high":
            score += 10
        if equity_pct < 25:
            score += 8
        if emergency_fund_months >= 6:
            score += 5

    elif action == "DIVERSIFY_PORTFOLIO":
        if diversification_score <= 1:
            score += 15
        elif diversification_score == 2:
            score += 8
        if portfolio_total > 100000:
            score += 10
        if risk_level == "medium":
            score += 5
        if goal_years > 5:
            score += 5

    elif action == "HOLD":
        # HOLD is the fallback — lower base, boost if profile is stable
        score = 55
        if emergency_fund_months >= 4:
            score += 8
        if debt_to_income < 0.3:
            score += 7
        if 30 <= equity_pct <= 60:
            score += 7
        if diversification_score >= 5:
            score += 5

    return min(score, 97)  # cap at 97% — never claim 100% certainty


def predict(salary, monthly_savings, goal_years, risk_level,
            dependents, investment_experience, emergency_fund_months,
            debt_to_income, current_equity_value, current_debt_value,
            sip_amount, sip_active, num_stocks, num_mutual_funds,
            income_type="salaried"):
    """
    Priority-based decision engine with 3 tiers:

      TIER 1 — SAFETY (always evaluated first, blocks lower tiers)
        Emergency fund, unaffordable SIP, imminent goal, extreme exposure

      TIER 2 — DEBT / STRUCTURAL (only if Tier 1 is clear)
        Rebalance, switch to debt, reduce over-commitment

      TIER 3 — GROWTH (only if Tier 1 and 2 are clear)
        SIP actions, buy, diversify, equity switch

    Returns: (action, confidence) tuple.
    """
    validate_inputs(salary, monthly_savings, goal_years, risk_level,
                    dependents, investment_experience, emergency_fund_months,
                    debt_to_income, current_equity_value, current_debt_value,
                    sip_amount, sip_active, num_stocks, num_mutual_funds,
                    income_type)

    # Derived features
    portfolio_total = current_equity_value + current_debt_value
    equity_pct = (current_equity_value / portfolio_total * 100) if portfolio_total > 0 else 0.0
    sip_ratio = (sip_amount / salary) if salary > 0 else 0.0
    diversification_score = num_stocks + num_mutual_funds

    action = None

    # ════════════════════════════════════════════
    #  TIER 1: SAFETY — non-negotiable, checked first
    # ════════════════════════════════════════════

    # 1a. No emergency fund at all — ALWAYS build first regardless of dependents
    if emergency_fund_months == 0:
        action = "EMERGENCY_FUND_BUILD"

    # 1b. Weak emergency fund with dependents or high debt
    elif emergency_fund_months < 3 and (dependents >= 1 or debt_to_income >= 0.35):
        action = "EMERGENCY_FUND_BUILD"

    # 1c. Minimal fund with heavy family burden
    elif emergency_fund_months < 4 and dependents >= 3:
        action = "EMERGENCY_FUND_BUILD"

    # 1d. SIP active but can't afford it
    if action is None and sip_active and monthly_savings < 3000:
        action = "STOP_SIP"

    # 1e. Goal imminent — lock in gains
    if action is None and goal_years < 2:
        action = "SELL"

    # 1f. Dangerously overexposed to equity
    if action is None and equity_pct > 80:
        action = "REBALANCE"

    # ════════════════════════════════════════════
    #  TIER 2: DEBT / STRUCTURAL — fix imbalances
    #  Only reached if no Tier 1 action triggered
    # ════════════════════════════════════════════

    if action is None:
        # 2a. High debt burden — don't invest, reduce commitments
        if debt_to_income >= 0.4 and sip_active and sip_ratio > 0.15:
            action = "REDUCE_SIP"

        # 2b. SIP too large for family situation
        elif sip_active and sip_ratio > 0.3 and dependents >= 3:
            action = "REDUCE_SIP"

        # 2c. Conservative investor with too much equity, short horizon
        elif risk_level == "low" and equity_pct > 50 and goal_years <= 5:
            action = "SWITCH_TO_DEBT"

        # 2d. Moderate overexposure to equity (65-80%) with short horizon
        elif equity_pct > 65 and goal_years <= 3 and risk_level != "high":
            action = "SWITCH_TO_DEBT"

    # ════════════════════════════════════════════
    #  TIER 3: GROWTH — invest and grow
    #  Only reached if Tier 1 & 2 are clear
    # ════════════════════════════════════════════

    if action is None:
        # 3a. SIP active — increase if strong position
        if sip_active and monthly_savings > 15000 and goal_years > 5:
            action = "INCREASE_SIP"

        # 3b. SIP active — continue if on track
        elif sip_active and monthly_savings >= 5000 and goal_years > 3:
            action = "CONTINUE_SIP"

        # 3c. No SIP — start if affordable
        elif not sip_active and monthly_savings > 10000 and goal_years > 5:
            action = "START_SIP"

        # 3d. Cheap equity entry for aggressive investors
        elif equity_pct < 30 and risk_level == "high":
            action = "BUY"

        # 3e. Long horizon, can switch to equity
        elif risk_level == "high" and equity_pct < 40 and goal_years > 7:
            action = "SWITCH_TO_EQUITY"

        # 3f. Concentrated portfolio
        elif diversification_score < 3 and portfolio_total > 50000:
            action = "DIVERSIFY_PORTFOLIO"

        # 3g. Default — everything is fine
        else:
            action = "HOLD"

    confidence = _compute_confidence(
        action, salary, monthly_savings, goal_years, risk_level,
        dependents, emergency_fund_months, debt_to_income,
        equity_pct, sip_active, sip_ratio, diversification_score,
        portfolio_total,
    )

    return action, confidence


# ──────────────────────────────────────────────
#  Action Intensity Engine
# ──────────────────────────────────────────────

def compute_intensity(action, salary, monthly_savings, goal_years, risk_level,
                      dependents, investment_experience, emergency_fund_months,
                      debt_to_income, current_equity_value, current_debt_value,
                      sip_amount, sip_active, num_stocks, num_mutual_funds,
                      income_type="salaried"):
    """
    Compute specific numeric intensity for each action.
    Instead of just "INCREASE_SIP", returns "INCREASE_SIP by INR 2,000/mo".

    Returns dict with:
        action_detail: str  (human-readable with numbers)
        metrics: dict       (raw computed values)
    """
    portfolio_total = current_equity_value + current_debt_value
    equity_pct = (current_equity_value / portfolio_total * 100) if portfolio_total > 0 else 0.0
    sip_ratio = (sip_amount / salary) if salary > 0 else 0.0

    if action == "INCREASE_SIP":
        # Target: SIP at 15-20% of salary, capped by affordable amount
        target_ratio = 0.15 if risk_level == "low" else (0.20 if risk_level == "medium" else 0.25)
        target_sip = int(salary * target_ratio)
        increase = max(1000, min(target_sip - sip_amount, int(monthly_savings * 0.3)))
        increase = (increase // 500) * 500  # round to nearest 500
        new_sip = sip_amount + increase
        return {
            "action_detail": f"Increase SIP by INR {increase:,}/mo (INR {sip_amount:,} → INR {new_sip:,})",
            "metrics": {
                "current_sip": sip_amount,
                "recommended_increase": increase,
                "new_sip": new_sip,
                "new_sip_ratio": round(new_sip / salary, 4) if salary > 0 else 0,
            },
        }

    elif action == "REDUCE_SIP":
        # Target: bring SIP ratio below 15% of salary
        target_sip = int(salary * 0.10)
        reduction = max(500, sip_amount - target_sip)
        reduction = (reduction // 500) * 500
        new_sip = max(500, sip_amount - reduction)
        return {
            "action_detail": f"Reduce SIP by INR {reduction:,}/mo (INR {sip_amount:,} → INR {new_sip:,})",
            "metrics": {
                "current_sip": sip_amount,
                "recommended_reduction": reduction,
                "new_sip": new_sip,
                "new_sip_ratio": round(new_sip / salary, 4) if salary > 0 else 0,
            },
        }

    elif action == "START_SIP":
        # Start at 10-15% of salary based on risk
        ratio = 0.10 if risk_level == "low" else (0.12 if risk_level == "medium" else 0.15)
        recommended = int(salary * ratio)
        recommended = (recommended // 500) * 500
        recommended = max(500, min(recommended, int(monthly_savings * 0.4)))
        return {
            "action_detail": f"Start SIP at INR {recommended:,}/mo ({round(recommended/salary*100, 1)}% of salary)",
            "metrics": {
                "recommended_sip": recommended,
                "sip_ratio": round(recommended / salary, 4) if salary > 0 else 0,
                "monthly_remaining": monthly_savings - recommended,
            },
        }

    elif action == "STOP_SIP":
        freed = sip_amount
        return {
            "action_detail": f"Stop SIP and free up INR {freed:,}/mo for essentials",
            "metrics": {
                "freed_amount": freed,
                "new_effective_savings": monthly_savings + freed,
            },
        }

    elif action == "REBALANCE":
        # Target: 60% equity for low, 65% medium, 70% high
        target_eq = 60 if risk_level == "low" else (65 if risk_level == "medium" else 70)
        shift_pct = round(equity_pct - target_eq, 1)
        shift_amount = int(portfolio_total * shift_pct / 100) if portfolio_total > 0 else 0
        return {
            "action_detail": f"Move INR {shift_amount:,} from equity to debt ({equity_pct:.0f}% → {target_eq}% equity)",
            "metrics": {
                "current_equity_pct": round(equity_pct, 1),
                "target_equity_pct": target_eq,
                "shift_pct": shift_pct,
                "shift_amount": shift_amount,
            },
        }

    elif action == "SELL":
        # Sell enough equity to meet goal or reduce exposure
        sell_pct = min(equity_pct, 40 if risk_level == "low" else 30)
        sell_amount = int(current_equity_value * sell_pct / 100)
        return {
            "action_detail": f"Sell INR {sell_amount:,} of equity holdings ({sell_pct:.0f}% of equity)",
            "metrics": {
                "sell_amount": sell_amount,
                "sell_pct_of_equity": sell_pct,
                "remaining_equity": current_equity_value - sell_amount,
            },
        }

    elif action == "BUY":
        # Invest a portion of savings into equity
        buy_amount = int(monthly_savings * 0.4) if risk_level == "high" else int(monthly_savings * 0.25)
        buy_amount = (buy_amount // 500) * 500
        return {
            "action_detail": f"Invest INR {buy_amount:,}/mo into equities",
            "metrics": {
                "monthly_buy": buy_amount,
                "annual_investment": buy_amount * 12,
                "remaining_savings": monthly_savings - buy_amount,
            },
        }

    elif action == "EMERGENCY_FUND_BUILD":
        # Target: 6 months of expenses (salary - savings = expenses)
        monthly_expenses = salary - monthly_savings
        target_months = 6
        current_fund = monthly_expenses * emergency_fund_months
        target_fund = monthly_expenses * target_months
        gap = max(0, target_fund - current_fund)
        monthly_allocation = min(int(monthly_savings * 0.5), int(gap / max(1, goal_years * 4)))
        monthly_allocation = max(1000, (monthly_allocation // 500) * 500)
        months_to_goal = int(gap / monthly_allocation) if monthly_allocation > 0 else 0
        return {
            "action_detail": f"Save INR {monthly_allocation:,}/mo toward emergency fund (INR {gap:,} gap, ~{months_to_goal} months)",
            "metrics": {
                "current_fund": current_fund,
                "target_fund": target_fund,
                "gap": gap,
                "monthly_allocation": monthly_allocation,
                "months_to_target": months_to_goal,
            },
        }

    elif action == "SWITCH_TO_DEBT":
        # Move a portion from equity to debt
        shift_pct = min(30, equity_pct - 40)
        shift_amount = int(current_equity_value * shift_pct / 100)
        new_equity_pct = round(equity_pct - shift_pct, 1)
        return {
            "action_detail": f"Shift INR {shift_amount:,} from equity to debt funds ({equity_pct:.0f}% → {new_equity_pct}% equity)",
            "metrics": {
                "shift_amount": shift_amount,
                "new_equity_pct": new_equity_pct,
                "instruments": "debt mutual funds, FDs, or bonds",
            },
        }

    elif action == "SWITCH_TO_EQUITY":
        shift_pct = min(20, 50 - equity_pct) if equity_pct < 50 else 10
        shift_amount = int(current_debt_value * shift_pct / 100) if current_debt_value > 0 else int(monthly_savings * 3)
        return {
            "action_detail": f"Move INR {shift_amount:,} from debt to equity ({equity_pct:.0f}% → {equity_pct + shift_pct:.0f}% equity)",
            "metrics": {
                "shift_amount": shift_amount,
                "new_equity_pct": round(equity_pct + shift_pct, 1),
                "instruments": "index funds, blue-chip stocks, or equity MFs",
            },
        }

    elif action == "DIVERSIFY_PORTFOLIO":
        target_instruments = max(5, num_stocks + num_mutual_funds + 3)
        add_stocks = max(1, (target_instruments - num_stocks - num_mutual_funds) // 2)
        add_mf = max(1, target_instruments - num_stocks - num_mutual_funds - add_stocks)
        monthly_invest = min(int(monthly_savings * 0.3), 5000)
        monthly_invest = (monthly_invest // 500) * 500
        return {
            "action_detail": f"Add {add_stocks} stocks + {add_mf} mutual funds, invest INR {monthly_invest:,}/mo across new instruments",
            "metrics": {
                "current_instruments": num_stocks + num_mutual_funds,
                "target_instruments": target_instruments,
                "add_stocks": add_stocks,
                "add_mutual_funds": add_mf,
                "monthly_diversification_amount": monthly_invest,
            },
        }

    elif action == "CONTINUE_SIP":
        return {
            "action_detail": f"Continue SIP at INR {sip_amount:,}/mo — on track ({sip_ratio:.1%} of salary)",
            "metrics": {
                "current_sip": sip_amount,
                "sip_ratio": round(sip_ratio, 4),
                "projected_annual": sip_amount * 12,
            },
        }

    else:  # HOLD
        return {
            "action_detail": "Hold current positions — no changes needed",
            "metrics": {
                "portfolio_total": portfolio_total,
                "equity_pct": round(equity_pct, 1),
                "status": "stable",
            },
        }


# ──────────────────────────────────────────────
#  Chained (Multi-Step) Decision Engine
# ──────────────────────────────────────────────

# Priority tiers for ordering the chain
_PRIORITY = {
    "EMERGENCY_FUND_BUILD": (1, "immediate"),
    "STOP_SIP":             (1, "immediate"),
    "REDUCE_SIP":           (1, "immediate"),
    "SELL":                 (1, "immediate"),
    "REBALANCE":            (2, "short_term"),
    "SWITCH_TO_DEBT":       (2, "short_term"),
    "SWITCH_TO_EQUITY":     (2, "short_term"),
    "DIVERSIFY_PORTFOLIO":  (2, "short_term"),
    "START_SIP":            (3, "long_term"),
    "INCREASE_SIP":         (3, "long_term"),
    "CONTINUE_SIP":         (3, "long_term"),
    "BUY":                  (3, "long_term"),
    "HOLD":                 (4, "long_term"),
}


def predict_chain(salary, monthly_savings, goal_years, risk_level,
                  dependents, investment_experience, emergency_fund_months,
                  debt_to_income, current_equity_value, current_debt_value,
                  sip_amount, sip_active, num_stocks, num_mutual_funds,
                  income_type="salaried"):
    """
    Multi-step chained decision engine.
    Evaluates ALL applicable rules and returns an ordered action plan.

    Returns: list of dicts, each with:
        step, action, confidence, phase, reason
    """
    validate_inputs(salary, monthly_savings, goal_years, risk_level,
                    dependents, investment_experience, emergency_fund_months,
                    debt_to_income, current_equity_value, current_debt_value,
                    sip_amount, sip_active, num_stocks, num_mutual_funds,
                    income_type)

    # Derived features
    portfolio_total = current_equity_value + current_debt_value
    equity_pct = (current_equity_value / portfolio_total * 100) if portfolio_total > 0 else 0.0
    sip_ratio = (sip_amount / salary) if salary > 0 else 0.0
    diversification_score = num_stocks + num_mutual_funds

    conf_args = (salary, monthly_savings, goal_years, risk_level,
                 dependents, emergency_fund_months, debt_to_income,
                 equity_pct, sip_active, sip_ratio, diversification_score,
                 portfolio_total)

    # Evaluate every rule independently, respecting priority tiers
    triggered = []

    # ── TIER 1: SAFETY ──
    if emergency_fund_months == 0:
        triggered.append("EMERGENCY_FUND_BUILD")
    elif emergency_fund_months < 3 and (dependents >= 1 or debt_to_income >= 0.35):
        triggered.append("EMERGENCY_FUND_BUILD")
    elif emergency_fund_months < 4 and dependents >= 3:
        triggered.append("EMERGENCY_FUND_BUILD")

    if sip_active and monthly_savings < 3000:
        triggered.append("STOP_SIP")

    if goal_years < 2:
        triggered.append("SELL")

    if equity_pct > 80:
        triggered.append("REBALANCE")

    # ── TIER 2: DEBT / STRUCTURAL ──
    if debt_to_income >= 0.4 and sip_active and sip_ratio > 0.15:
        triggered.append("REDUCE_SIP")

    if sip_active and sip_ratio > 0.3 and dependents >= 3:
        if "REDUCE_SIP" not in triggered:
            triggered.append("REDUCE_SIP")

    if risk_level == "low" and equity_pct > 50 and goal_years <= 5:
        triggered.append("SWITCH_TO_DEBT")

    if equity_pct > 65 and goal_years <= 3 and risk_level != "high":
        if "SWITCH_TO_DEBT" not in triggered:
            triggered.append("SWITCH_TO_DEBT")

    if risk_level == "high" and equity_pct < 40 and goal_years > 7:
        triggered.append("SWITCH_TO_EQUITY")

    if diversification_score < 3 and portfolio_total > 50000:
        triggered.append("DIVERSIFY_PORTFOLIO")

    # ── TIER 3: GROWTH (only if no safety issues block it) ──
    has_safety_issue = "EMERGENCY_FUND_BUILD" in triggered or "STOP_SIP" in triggered

    if not has_safety_issue:
        if not sip_active and monthly_savings > 10000 and goal_years > 5:
            triggered.append("START_SIP")

        if sip_active and monthly_savings > 15000 and goal_years > 5:
            triggered.append("INCREASE_SIP")

        if sip_active and monthly_savings >= 5000 and goal_years > 3:
            sip_actions = {"STOP_SIP", "INCREASE_SIP", "REDUCE_SIP"}
            if not sip_actions.intersection(triggered):
                triggered.append("CONTINUE_SIP")

        if equity_pct < 30 and risk_level == "high":
            triggered.append("BUY")

    # If nothing triggered, HOLD
    if not triggered:
        triggered.append("HOLD")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for a in triggered:
        if a not in seen:
            seen.add(a)
            unique.append(a)

    # Sort by priority tier, then by original trigger order within tier
    unique.sort(key=lambda a: (_PRIORITY.get(a, (4, "long_term"))[0], triggered.index(a)))

    # Build the chain
    chain = []
    for i, action in enumerate(unique, 1):
        priority_num, phase = _PRIORITY.get(action, (4, "long_term"))
        confidence = _compute_confidence(action, *conf_args)
        chain.append({
            "step": i,
            "action": action,
            "description": ACTION_DESCRIPTIONS[action],
            "confidence": confidence,
            "phase": phase,
        })

    return chain


# ──────────────────────────────────────────────
#  Interactive CLI (no ML dependencies)
# ──────────────────────────────────────────────

def _ask_int(prompt, lo, hi):
    while True:
        try:
            val = int(input(f"  {prompt} [{lo}-{hi}]: "))
            if lo <= val <= hi:
                return val
            print(f"    Must be between {lo} and {hi}.")
        except ValueError:
            print("    Enter a valid integer.")


def _ask_float(prompt, lo, hi):
    while True:
        try:
            val = float(input(f"  {prompt} [{lo}-{hi}]: "))
            if lo <= val <= hi:
                return round(val, 2)
            print(f"    Must be between {lo} and {hi}.")
        except ValueError:
            print("    Enter a valid number.")


def _ask_choice(prompt, choices):
    while True:
        val = input(f"  {prompt} [{' / '.join(choices)}]: ").strip().lower()
        if val in choices:
            return val
        print(f"    Must be one of: {', '.join(choices)}")


def _ask_bool(prompt):
    while True:
        val = input(f"  {prompt} [yes / no]: ").strip().lower()
        if val in ("yes", "y", "true"):
            return True
        if val in ("no", "n", "false"):
            return False
        print("    Enter yes or no.")


def run_rule_engine():
    """Standalone interactive prediction — zero ML dependencies."""
    print()
    print("=" * 55)
    print("  AI FINANCIAL DECISION ENGINE v2")
    print("  Context-Aware Rule-Based (no ML runtime needed)")
    print("=" * 55)

    while True:
        print()
        print("-" * 55)
        print("  ENTER YOUR FINANCIAL PROFILE")
        print("-" * 55)

        salary = _ask_int("Monthly salary (INR)", 5000, 500000)
        monthly_savings = _ask_int("Monthly savings (INR)", 500, 200000)
        goal_years = _ask_int("Years to financial goal", 1, 15)
        risk_level = _ask_choice("Risk tolerance", ["low", "medium", "high"])
        dependents = _ask_int("Number of dependents", 0, 5)
        experience = _ask_choice("Investment experience", ["beginner", "intermediate", "expert"])
        emergency = _ask_int("Emergency fund (months)", 0, 12)
        dti = _ask_float("Debt-to-income ratio", 0, 0.6)

        print()
        print("-" * 55)
        print("  CURRENT HOLDINGS & SIP")
        print("-" * 55)

        equity_val = _ask_int("Current equity value (INR)", 0, 500000)
        debt_val = _ask_int("Current debt value (INR)", 0, 500000)
        sip_active = _ask_bool("SIP currently active?")
        sip_amount = _ask_int("SIP amount (INR/month)", 0, 25000) if sip_active else 0
        num_stocks = _ask_int("Number of stocks held", 0, 20)
        num_mf = _ask_int("Number of mutual funds", 0, 15)

        action, confidence = predict(
            salary=salary, monthly_savings=monthly_savings,
            goal_years=goal_years, risk_level=risk_level,
            dependents=dependents, investment_experience=experience,
            emergency_fund_months=emergency, debt_to_income=dti,
            current_equity_value=equity_val, current_debt_value=debt_val,
            sip_amount=sip_amount, sip_active=sip_active,
            num_stocks=num_stocks, num_mutual_funds=num_mf,
        )

        # Compute derived for display
        portfolio_total = equity_val + debt_val
        equity_pct = (equity_val / portfolio_total * 100) if portfolio_total > 0 else 0.0

        print()
        print("=" * 55)
        print("  RECOMMENDATION")
        print("=" * 55)
        print(f"  Action       : {action}")
        print(f"  Confidence   : {confidence}%")
        print(f"  Reason       : {ACTION_DESCRIPTIONS[action]}")
        print(f"  Portfolio    : INR {portfolio_total:,} ({equity_pct:.1f}% equity)")
        print(f"  SIP Status   : {'Active @ INR ' + str(sip_amount) + '/mo' if sip_active else 'Inactive'}")
        print(f"  Diversification : {num_stocks} stocks + {num_mf} funds = {num_stocks + num_mf} instruments")
        print("=" * 55)

        again = input("\n  Run another? (y/n): ").strip().lower()
        if again != "y":
            print("\n  Goodbye!\n")
            break


if __name__ == "__main__":
    run_rule_engine()
