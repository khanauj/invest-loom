"""
risk_scorer.py - Computed Risk Score Engine

Replaces static risk_level (low/medium/high) with a granular 0-100 risk score
calculated from 5 financial dimensions:

  1. Income Stability   — savings ratio, salary level, income type, volatility
  2. Dependency Burden  — dependents, debt-to-income
  3. Safety Net         — emergency fund coverage
  4. Portfolio Volatility — equity concentration, diversification
  5. Time Horizon       — years to goal, investment experience

Score Interpretation:
    0-25   = Very Low Risk   (conservative, well-protected)
   26-45   = Low Risk
   46-60   = Moderate Risk
   61-75   = High Risk
   76-100  = Very High Risk  (aggressive, exposed)

Higher score = MORE risk exposure = needs more protective actions.
"""


# ──────────────────────────────────────────────
#  Income Type Definitions
# ──────────────────────────────────────────────

INCOME_TYPES = {
    "salaried": {
        "label": "Salaried (Fixed)",
        "base_stability": 0.85,
        "volatility": 0.10,
        "description": "Regular fixed salary from employer",
    },
    "freelance": {
        "label": "Freelance / Contract",
        "base_stability": 0.50,
        "volatility": 0.45,
        "description": "Project-based income, variable monthly inflow",
    },
    "business": {
        "label": "Business Owner",
        "base_stability": 0.55,
        "volatility": 0.40,
        "description": "Self-employed with business income",
    },
    "mixed": {
        "label": "Mixed (Salary + Side Income)",
        "base_stability": 0.70,
        "volatility": 0.25,
        "description": "Primary salary plus secondary income streams",
    },
    "pension": {
        "label": "Pension / Retired",
        "base_stability": 0.90,
        "volatility": 0.05,
        "description": "Fixed pension or retirement income",
    },
}


def _compute_income_stability_detail(salary, monthly_savings, sip_amount, sip_active,
                                      income_type="salaried"):
    """
    Compute detailed income stability metrics.

    Returns:
        income_type: str — type of income
        stability_score: float 0-1 — how stable the income is
        volatility: float 0-1 — how much income varies month to month
        income_risk: int 0-20 — risk contribution to total score
    """
    type_info = INCOME_TYPES.get(income_type, INCOME_TYPES["salaried"])
    base_stability = type_info["base_stability"]
    base_volatility = type_info["volatility"]

    savings_ratio = monthly_savings / salary if salary > 0 else 0

    # Adjust stability based on savings behavior
    # High savings ratio = more stable financial position regardless of income type
    savings_bonus = 0
    if savings_ratio >= 0.40:
        savings_bonus = 0.10
    elif savings_ratio >= 0.25:
        savings_bonus = 0.07
    elif savings_ratio >= 0.15:
        savings_bonus = 0.04

    # Salary level adjustment (higher salary = more options = more stability)
    salary_bonus = 0
    if salary >= 70000:
        salary_bonus = 0.08
    elif salary >= 50000:
        salary_bonus = 0.05
    elif salary >= 35000:
        salary_bonus = 0.02

    # SIP consistency indicates income discipline
    sip_bonus = 0
    if sip_active:
        sip_ratio = sip_amount / salary if salary > 0 else 0
        if sip_ratio > 0.30:
            sip_bonus = -0.05  # over-committed = less stable
            base_volatility += 0.05
        elif sip_ratio <= 0.15:
            sip_bonus = 0.03  # comfortable commitment

    # Final stability score (0-1)
    stability_score = min(1.0, max(0.0, base_stability + savings_bonus + salary_bonus + sip_bonus))

    # Final volatility (0-1, adjusted by savings buffer)
    volatility = max(0.0, min(1.0, base_volatility - (savings_bonus * 0.5)))

    # Convert to risk score (0-20): lower stability = higher risk
    income_risk = int((1.0 - stability_score) * 20)
    income_risk = max(0, min(20, income_risk))

    return {
        "income_type": income_type,
        "income_type_label": type_info["label"],
        "stability_score": round(stability_score, 2),
        "volatility": round(volatility, 2),
        "income_risk": income_risk,
        "savings_ratio": round(savings_ratio, 3),
    }


def compute_risk_score(salary, monthly_savings, goal_years, risk_level,
                       dependents, investment_experience, emergency_fund_months,
                       debt_to_income, current_equity_value, current_debt_value,
                       sip_amount, sip_active, num_stocks, num_mutual_funds,
                       income_type="salaried"):
    """
    Compute a granular risk score (0-100) from the user's financial profile.

    Returns dict with:
        risk_score: int 0-100
        risk_label: str (very_low / low / moderate / high / very_high)
        breakdown: dict with per-dimension scores and explanations
    """
    portfolio_total = current_equity_value + current_debt_value
    equity_pct = (current_equity_value / portfolio_total * 100) if portfolio_total > 0 else 0.0
    savings_ratio = monthly_savings / salary if salary > 0 else 0
    diversification_score = num_stocks + num_mutual_funds

    # ── Dimension 1: Income Stability (0-20) ──
    # Now uses detailed income type + stability + volatility model
    income_detail = _compute_income_stability_detail(
        salary, monthly_savings, sip_amount, sip_active, income_type,
    )
    income_risk = income_detail["income_risk"]

    # ── Dimension 2: Dependency Burden (0-20) ──
    # More dependents + higher DTI = MORE risk
    dep_risk = 0
    dep_risk += min(dependents * 3, 12)  # 0-12 from dependents
    dep_risk += int(debt_to_income * 20)  # 0-12 from DTI (0.6 * 20 = 12)
    dep_risk = min(20, dep_risk)

    # ── Dimension 3: Safety Net (0-20) ──
    # Less emergency fund = MORE risk
    if emergency_fund_months == 0:
        safety_risk = 20
    elif emergency_fund_months <= 2:
        safety_risk = 16
    elif emergency_fund_months <= 4:
        safety_risk = 10
    elif emergency_fund_months <= 6:
        safety_risk = 5
    elif emergency_fund_months <= 9:
        safety_risk = 2
    else:
        safety_risk = 0

    # ── Dimension 4: Portfolio Volatility (0-20) ──
    # High equity concentration + low diversification = MORE risk
    vol_risk = 0
    if equity_pct > 80:
        vol_risk += 14
    elif equity_pct > 60:
        vol_risk += 10
    elif equity_pct > 40:
        vol_risk += 6
    else:
        vol_risk += 2

    if diversification_score <= 1:
        vol_risk += 6
    elif diversification_score <= 3:
        vol_risk += 4
    elif diversification_score <= 5:
        vol_risk += 2
    vol_risk = min(20, vol_risk)

    # ── Dimension 5: Time Horizon & Experience (0-20) ──
    # Short horizon + beginner = MORE risk
    horizon_risk = 0
    if goal_years <= 2:
        horizon_risk += 12
    elif goal_years <= 5:
        horizon_risk += 8
    elif goal_years <= 8:
        horizon_risk += 4
    else:
        horizon_risk += 1

    if investment_experience == "beginner":
        horizon_risk += 8
    elif investment_experience == "intermediate":
        horizon_risk += 4
    else:
        horizon_risk += 1
    horizon_risk = min(20, horizon_risk)

    # ── Total ──
    total = income_risk + dep_risk + safety_risk + vol_risk + horizon_risk
    total = max(0, min(100, total))

    # Label
    if total <= 25:
        label = "very_low"
    elif total <= 45:
        label = "low"
    elif total <= 60:
        label = "moderate"
    elif total <= 75:
        label = "high"
    else:
        label = "very_high"

    # Safety net quality label
    if emergency_fund_months >= 6:
        safety_quality = "good"
    elif emergency_fund_months >= 3:
        safety_quality = "adequate"
    elif emergency_fund_months >= 1:
        safety_quality = "weak"
    else:
        safety_quality = "none"

    # Salary shorthand
    if salary >= 100000:
        salary_str = f"INR {salary // 100000}L"
    elif salary >= 1000:
        salary_str = f"INR {salary // 1000}k"
    else:
        salary_str = f"INR {salary}"

    # Dependent singular/plural
    dep_word = "dependent" if dependents == 1 else "dependents"

    return {
        "risk_score": total,
        "risk_label": label,
        "income_stability_detail": income_detail,
        "breakdown": {
            "income_stability": {
                "score": income_risk,
                "max": 20,
                "detail": f"{savings_ratio:.1%} savings ratio, {salary_str} salary, {income_detail['income_type_label']}",
                "stability_score": income_detail["stability_score"],
                "volatility": income_detail["volatility"],
                "income_type": income_detail["income_type"],
            },
            "dependency_burden": {
                "score": dep_risk,
                "max": 20,
                "detail": f"{dependents} {dep_word}, {debt_to_income:.0%} DTI",
            },
            "safety_net": {
                "score": safety_risk,
                "max": 20,
                "detail": f"{emergency_fund_months} months fund -- {safety_quality}",
            },
            "portfolio_volatility": {
                "score": vol_risk,
                "max": 20,
                "detail": f"{equity_pct:.1f}% equity, {diversification_score} instruments",
            },
            "time_horizon": {
                "score": horizon_risk,
                "max": 20,
                "detail": f"{goal_years}yr goal, {investment_experience}",
            },
        },
    }
