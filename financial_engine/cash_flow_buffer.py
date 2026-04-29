"""
cash_flow_buffer.py - Cash Flow Buffer Engine

Computes how long a user can survive without income based on:
  - Total liquid savings (emergency fund + accessible savings)
  - Monthly expenses (salary - monthly_savings + debt obligations)
  - SIP commitments (can be paused in emergency)

Output:
    survival_months: float  — how many months user can survive with zero income
    buffer_rating: str      — critical / weak / adequate / strong / fortress
    monthly_inflow: int     — total monthly income
    monthly_outflow: int    — total monthly expenses (fixed + variable)
    monthly_surplus: int    — inflow - outflow
    buffer_breakdown: dict  — detailed cash flow components

Higher survival_months = MORE financial resilience.
"""


# ──────────────────────────────────────────────
#  Buffer Rating Thresholds
# ──────────────────────────────────────────────

BUFFER_RATINGS = [
    (1,   "critical"),    # <1 month — immediate danger
    (3,   "weak"),        # 1-3 months — one paycheck away from trouble
    (6,   "adequate"),    # 3-6 months — standard recommendation
    (9,   "strong"),      # 6-9 months — well-protected
    (999, "fortress"),    # 9+ months — exceptional buffer
]

# Expense estimation: what percentage of salary goes to fixed costs
# Used when we don't have itemized expense data
EXPENSE_ESTIMATION = {
    "rent_pct": 0.30,          # 30% of salary to rent/housing
    "essentials_pct": 0.20,    # 20% to food, transport, utilities
    "debt_service_pct": None,  # computed from debt_to_income
    "discretionary_pct": 0.10, # 10% discretionary (can be cut in emergency)
}


def compute_cash_flow_buffer(salary, monthly_savings, emergency_fund_months,
                              debt_to_income, sip_amount, sip_active,
                              current_equity_value=0, current_debt_value=0,
                              **kwargs):
    """
    Compute cash flow buffer analysis.

    Args:
        salary: Monthly salary (INR)
        monthly_savings: Amount saved per month (INR)
        emergency_fund_months: Months of expenses in emergency fund
        debt_to_income: Debt-to-income ratio (0.0 - 0.6)
        sip_amount: Monthly SIP commitment (INR)
        sip_active: Whether SIP is currently running
        current_equity_value: Equity portfolio value (INR)
        current_debt_value: Debt instrument value (INR)

    Returns dict with:
        survival_months, buffer_rating, monthly breakdown, and actionable insights
    """
    # ── Monthly Income ──
    monthly_inflow = salary

    # ── Monthly Expenses (estimated) ──
    # Expenses = salary - savings (what you spend each month)
    monthly_expenses = salary - monthly_savings
    monthly_expenses = max(monthly_expenses, 0)

    # Debt service component
    debt_service = int(salary * debt_to_income)

    # SIP commitment (can be paused but counts as current outflow)
    sip_outflow = sip_amount if sip_active else 0

    # Non-discretionary expenses (cannot be cut easily)
    fixed_expenses = int(monthly_expenses * 0.70)  # 70% of spending is fixed
    variable_expenses = monthly_expenses - fixed_expenses  # 30% can be cut

    # Monthly surplus (what's left after ALL spending)
    monthly_surplus = salary - monthly_expenses

    # ── Liquid Savings (what can be accessed in emergency) ──
    # Emergency fund = emergency_fund_months * monthly_expenses
    emergency_fund_value = emergency_fund_months * monthly_expenses

    # Liquid accessible savings = emergency fund + a portion of debt instruments
    # (Equity is NOT liquid in emergency — selling takes time + may be at loss)
    # Debt instruments are partially liquid (70% accessible within 1-7 days)
    liquid_from_debt = int(current_debt_value * 0.70)

    total_liquid_savings = emergency_fund_value + liquid_from_debt

    # ── Survival Months ──
    # If income drops to 0, how long can user survive?
    # In emergency mode: cut discretionary spending, pause SIP
    emergency_monthly_burn = fixed_expenses  # only fixed costs survive

    if emergency_monthly_burn > 0:
        survival_months = round(total_liquid_savings / emergency_monthly_burn, 1)
    else:
        survival_months = 99.0  # no expenses = infinite survival

    # Cap at 36 months for display
    survival_months = min(survival_months, 36.0)

    # ── Buffer Rating ──
    buffer_rating = "fortress"
    for threshold, rating in BUFFER_RATINGS:
        if survival_months < threshold:
            buffer_rating = rating
            break

    # ── Savings Runway (different from survival) ──
    # How long can current savings + investments last at CURRENT spending rate?
    total_assets = emergency_fund_value + current_equity_value + current_debt_value
    if monthly_expenses > 0:
        full_runway_months = round(total_assets / monthly_expenses, 1)
    else:
        full_runway_months = 99.0
    full_runway_months = min(full_runway_months, 60.0)

    # ── SIP Sustainability ──
    # What % of income goes to SIP? Is it sustainable?
    sip_ratio = sip_amount / salary if salary > 0 else 0
    if sip_ratio > 0.35:
        sip_sustainability = "over_committed"
    elif sip_ratio > 0.25:
        sip_sustainability = "stretched"
    elif sip_ratio > 0.10:
        sip_sustainability = "comfortable"
    elif sip_ratio > 0:
        sip_sustainability = "light"
    else:
        sip_sustainability = "none"

    # ── Actionable Insights ──
    insights = []

    if survival_months < 1:
        insights.append("URGENT: Less than 1 month of buffer. Build emergency fund immediately.")
    elif survival_months < 3:
        insights.append("WARNING: Buffer below 3 months. Prioritize liquid savings over investments.")

    if debt_to_income >= 0.40:
        insights.append(f"High debt burden ({debt_to_income:.0%} DTI) is eating into your buffer capacity.")

    if sip_active and sip_sustainability == "over_committed":
        insights.append(f"SIP at {sip_ratio:.0%} of income is over-committed. Reduce to build buffer first.")

    if emergency_fund_months < 3 and current_equity_value > emergency_fund_value:
        insights.append("You have more in equity than in emergency fund. Redirect some savings to liquid assets.")

    if survival_months >= 6 and sip_sustainability in ("comfortable", "light"):
        insights.append("Strong buffer position. Safe to increase SIP or explore equity investments.")

    if survival_months >= 9:
        insights.append("Fortress-level buffer. Consider deploying excess liquid savings into growth assets.")

    # ── Recommended Buffer Target ──
    # Standard: 6 months of expenses; 9 months if dependents or high DTI
    recommended_buffer_months = 6
    if debt_to_income >= 0.30:
        recommended_buffer_months = 9

    recommended_buffer_value = recommended_buffer_months * monthly_expenses
    buffer_gap = max(0, recommended_buffer_value - emergency_fund_value)
    months_to_fill_gap = int(buffer_gap / monthly_savings) if monthly_savings > 0 else 99

    return {
        "survival_months": survival_months,
        "buffer_rating": buffer_rating,
        "monthly_inflow": monthly_inflow,
        "monthly_outflow": monthly_expenses,
        "monthly_surplus": monthly_surplus,
        "emergency_monthly_burn": emergency_monthly_burn,
        "buffer_breakdown": {
            "emergency_fund_value": emergency_fund_value,
            "liquid_from_debt_instruments": liquid_from_debt,
            "total_liquid_savings": total_liquid_savings,
            "fixed_expenses": fixed_expenses,
            "variable_expenses": variable_expenses,
            "debt_service": debt_service,
            "sip_outflow": sip_outflow,
        },
        "full_runway_months": full_runway_months,
        "sip_sustainability": sip_sustainability,
        "recommended_buffer": {
            "target_months": recommended_buffer_months,
            "target_value": recommended_buffer_value,
            "current_value": emergency_fund_value,
            "gap": buffer_gap,
            "months_to_fill": months_to_fill_gap,
        },
        "insights": insights,
    }


def format_cash_flow_buffer(result):
    """Format cash flow buffer for display output."""
    lines = []

    def indian(n):
        if n < 0:
            return "-" + indian(-n)
        s = str(int(n))
        if len(s) <= 3:
            return s
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while rest:
            groups.append(rest[-2:])
            rest = rest[:-2]
        groups.reverse()
        return ",".join(groups) + "," + last3

    rating = result["buffer_rating"].upper()
    survival = result["survival_months"]
    bd = result["buffer_breakdown"]

    lines.append(f"  Survival Months: {survival:.1f} months ({rating})")
    lines.append("")

    # Cash flow summary
    lines.append(f"  MONTHLY CASH FLOW:")
    lines.append(f"    Income (salary)          INR {indian(result['monthly_inflow']):>9s}")
    lines.append(f"    Fixed expenses           INR {indian(bd['fixed_expenses']):>9s}")
    lines.append(f"    Variable expenses        INR {indian(bd['variable_expenses']):>9s}")
    lines.append(f"    Debt service             INR {indian(bd['debt_service']):>9s}")
    if bd['sip_outflow'] > 0:
        lines.append(f"    SIP commitment           INR {indian(bd['sip_outflow']):>9s}")
    lines.append(f"    {'':27s} ─────────────")
    lines.append(f"    Monthly surplus          INR {indian(result['monthly_surplus']):>9s}")

    # Liquid reserves
    lines.append("")
    lines.append(f"  LIQUID RESERVES:")
    lines.append(f"    Emergency fund           INR {indian(bd['emergency_fund_value']):>9s}")
    lines.append(f"    Liquid debt instruments   INR {indian(bd['liquid_from_debt_instruments']):>9s}")
    lines.append(f"    {'':27s} ─────────────")
    lines.append(f"    Total accessible         INR {indian(bd['total_liquid_savings']):>9s}")

    # Emergency burn rate
    lines.append("")
    lines.append(f"  Emergency burn rate: INR {indian(result['emergency_monthly_burn'])}/mo (fixed costs only)")
    lines.append(f"  Full runway (all assets):  {result['full_runway_months']:.1f} months")
    lines.append(f"  SIP sustainability:        {result['sip_sustainability'].upper().replace('_', ' ')}")

    # Buffer target
    rec = result["recommended_buffer"]
    lines.append("")
    lines.append(f"  BUFFER TARGET:")
    lines.append(f"    Recommended:  {rec['target_months']} months = INR {indian(rec['target_value'])}")
    lines.append(f"    Current:      INR {indian(rec['current_value'])}")
    if rec["gap"] > 0:
        lines.append(f"    Gap:          INR {indian(rec['gap'])} ({rec['months_to_fill']} months to fill)")
    else:
        lines.append(f"    Status:       TARGET MET")

    # Insights
    if result["insights"]:
        lines.append("")
        lines.append("  INSIGHTS:")
        for insight in result["insights"]:
            lines.append(f"    -> {insight}")

    return "\n".join(lines)
