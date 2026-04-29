"""
income_shock_simulator.py - Income Shock Simulation Engine

Simulates extreme income scenarios and measures financial resilience:

  Scenario 1: Income drops 50% for 6 months
  Scenario 2: Income = 0 for 3 months (job loss)
  Scenario 3: Income = 0 for 6 months (extended unemployment)
  Scenario 4: Income drops 30% permanently (pay cut / career change)

For each scenario, computes:
  - Can user survive the shock period?
  - How many months of buffer remain after shock?
  - Impact on each financial goal (delay in months)
  - Recovery timeline (months to return to pre-shock position)
  - Decision adjustments (what should change in the financial plan)

This is the most advanced layer — sits on TOP of:
  Income Stability → Cash Flow Buffer → Shock Simulation → Decision Adjustment
"""

from financial_engine.goal_planner import _required_monthly_sip, STRATEGY_RETURNS, _get_strategy


# ──────────────────────────────────────────────
#  Shock Scenarios
# ──────────────────────────────────────────────

SHOCK_SCENARIOS = {
    "income_drop_50": {
        "label": "50% Income Drop (6 months)",
        "description": "What if your income halves for 6 months? (e.g., business slowdown, reduced hours)",
        "income_multiplier": 0.50,
        "duration_months": 6,
    },
    "zero_income_3mo": {
        "label": "Zero Income for 3 Months",
        "description": "What if you earn nothing for 3 months? (e.g., job loss, medical leave)",
        "income_multiplier": 0.0,
        "duration_months": 3,
    },
    "zero_income_6mo": {
        "label": "Zero Income for 6 Months",
        "description": "What if you earn nothing for 6 months? (e.g., extended unemployment)",
        "income_multiplier": 0.0,
        "duration_months": 6,
    },
    "permanent_30_cut": {
        "label": "Permanent 30% Pay Cut",
        "description": "What if your income drops 30% forever? (e.g., career change, industry downturn)",
        "income_multiplier": 0.70,
        "duration_months": 12,  # analyze first 12 months impact
    },
}


# ──────────────────────────────────────────────
#  Scenario Simulation
# ──────────────────────────────────────────────

def _simulate_single_scenario(scenario_key, salary, monthly_savings, monthly_expenses,
                               emergency_fund_value, total_liquid_savings,
                               sip_amount, sip_active, goals=None, risk_level="medium"):
    """
    Simulate a single shock scenario.

    Returns dict with survival analysis, goal impact, and recovery estimate.
    """
    scenario = SHOCK_SCENARIOS[scenario_key]
    income_mult = scenario["income_multiplier"]
    duration = scenario["duration_months"]

    # ── Shocked Income ──
    shocked_salary = int(salary * income_mult)
    shocked_savings_capacity = max(0, shocked_salary - monthly_expenses)

    # In shock: pause SIP, cut discretionary spending by 50%
    fixed_expenses = int(monthly_expenses * 0.70)
    variable_expenses = monthly_expenses - fixed_expenses
    emergency_expenses = fixed_expenses + int(variable_expenses * 0.50)  # cut variable by 50%

    # Monthly deficit during shock
    monthly_deficit = max(0, emergency_expenses - shocked_salary)

    # Total cash drain over shock period
    total_drain = monthly_deficit * duration

    # ── Survival Check ──
    can_survive = total_liquid_savings >= total_drain
    buffer_remaining = max(0, total_liquid_savings - total_drain)

    if monthly_deficit > 0:
        months_buffer_lasts = round(total_liquid_savings / monthly_deficit, 1)
    else:
        months_buffer_lasts = 99.0  # no deficit = infinite
    months_buffer_lasts = min(months_buffer_lasts, 36.0)

    survives_full_duration = months_buffer_lasts >= duration

    # ── Recovery Timeline ──
    # After shock ends, how many months to rebuild depleted savings?
    if total_drain > 0 and monthly_savings > 0:
        recovery_months = int(total_drain / monthly_savings) + 1
    else:
        recovery_months = 0

    # ── Goal Impact Analysis ──
    goal_impacts = []
    if goals:
        for goal in goals:
            name = goal["name"]
            target = goal["target"]
            saved = goal.get("saved", 0)
            years = goal["years"]
            priority = goal.get("priority", "medium")

            strategy = _get_strategy(years, risk_level)
            expected_return = STRATEGY_RETURNS[strategy]

            # Original monthly SIP needed
            original_sip = _required_monthly_sip(target, saved, expected_return, years)

            # During shock: SIP paused completely
            # After shock: SIP resumes but savings depleted
            # Impact: lost SIP contributions + lost compounding for `duration` months

            # Lost SIP contributions during shock period
            lost_contributions = original_sip * duration

            # Reduced time remaining after recovery
            # Effective time lost = shock duration + recovery period (in years)
            total_delay_months = duration + recovery_months
            effective_years_remaining = max(0.5, years - (total_delay_months / 12))

            # New monthly SIP needed after shock recovery
            # Savings reduced by amount used during shock
            savings_after_shock = max(0, saved - total_drain)
            new_sip_needed = _required_monthly_sip(target, savings_after_shock,
                                                     expected_return, effective_years_remaining)

            sip_increase = max(0, new_sip_needed - original_sip)
            delay_months = 0

            # If new SIP > original SIP + 20%, goal is delayed
            if original_sip > 0 and new_sip_needed > original_sip * 1.20:
                # Estimate delay: how many extra months at original SIP rate
                gap_after_shock = max(0, target - savings_after_shock)
                if original_sip > 0:
                    months_at_original = gap_after_shock / (original_sip * (1 + expected_return / 12))
                    original_months = max(0, target - saved) / (original_sip * (1 + expected_return / 12)) if original_sip > 0 else 0
                    delay_months = max(0, int(months_at_original - original_months))

            # Goal feasibility after shock
            if new_sip_needed == 0:
                feasibility = "SAFE"
            elif new_sip_needed <= original_sip * 1.10:
                feasibility = "MINIMAL IMPACT"
            elif new_sip_needed <= original_sip * 1.30:
                feasibility = "MODERATE IMPACT"
            elif new_sip_needed <= original_sip * 1.50:
                feasibility = "SIGNIFICANT DELAY"
            else:
                feasibility = "AT RISK"

            goal_impacts.append({
                "goal_name": name,
                "priority": priority,
                "original_sip": original_sip,
                "new_sip_needed": new_sip_needed,
                "sip_increase": sip_increase,
                "delay_months": delay_months,
                "lost_contributions": lost_contributions,
                "feasibility": feasibility,
            })

    # ── Severity Rating ──
    if not survives_full_duration:
        severity = "CRITICAL"
    elif buffer_remaining < emergency_expenses * 2:
        severity = "SEVERE"
    elif recovery_months > 12:
        severity = "HIGH"
    elif recovery_months > 6:
        severity = "MODERATE"
    else:
        severity = "LOW"

    return {
        "scenario": scenario_key,
        "label": scenario["label"],
        "description": scenario["description"],
        "shocked_salary": shocked_salary,
        "emergency_expenses": emergency_expenses,
        "monthly_deficit": monthly_deficit,
        "total_drain": total_drain,
        "can_survive": can_survive,
        "survives_full_duration": survives_full_duration,
        "months_buffer_lasts": months_buffer_lasts,
        "buffer_remaining": buffer_remaining,
        "recovery_months": recovery_months,
        "severity": severity,
        "goal_impacts": goal_impacts,
    }


# ──────────────────────────────────────────────
#  Full Shock Simulation
# ──────────────────────────────────────────────

def simulate_income_shocks(salary, monthly_savings, emergency_fund_months,
                            debt_to_income, sip_amount, sip_active,
                            current_equity_value=0, current_debt_value=0,
                            goals=None, risk_level="medium", **kwargs):
    """
    Run all shock scenarios and produce a comprehensive resilience report.

    Args:
        salary, monthly_savings, etc.: Standard financial profile fields
        goals: list of goal dicts (optional) for goal impact analysis
        risk_level: for goal strategy assignment

    Returns dict with:
        scenarios: dict of scenario results
        resilience_score: 0-100 (higher = more resilient)
        overall_verdict: str
        decision_adjustments: list of recommended changes
    """
    # Compute base values
    monthly_expenses = salary - monthly_savings
    monthly_expenses = max(monthly_expenses, 0)
    emergency_fund_value = emergency_fund_months * monthly_expenses

    # Liquid savings
    liquid_from_debt = int(current_debt_value * 0.70)
    total_liquid_savings = emergency_fund_value + liquid_from_debt

    # Run all scenarios
    scenarios = {}
    for key in SHOCK_SCENARIOS:
        scenarios[key] = _simulate_single_scenario(
            key, salary, monthly_savings, monthly_expenses,
            emergency_fund_value, total_liquid_savings,
            sip_amount, sip_active, goals, risk_level,
        )

    # ── Resilience Score (0-100) ──
    # Based on how many scenarios user survives + recovery speed
    score = 100

    for key, result in scenarios.items():
        if not result["survives_full_duration"]:
            score -= 25  # major penalty for each failed scenario
        elif result["severity"] == "SEVERE":
            score -= 15
        elif result["severity"] == "HIGH":
            score -= 10
        elif result["severity"] == "MODERATE":
            score -= 5

        # Recovery speed penalty
        if result["recovery_months"] > 12:
            score -= 5
        elif result["recovery_months"] > 6:
            score -= 2

    score = max(0, min(100, score))

    # ── Resilience Label ──
    if score >= 80:
        resilience_label = "HIGHLY RESILIENT"
    elif score >= 60:
        resilience_label = "MODERATELY RESILIENT"
    elif score >= 40:
        resilience_label = "VULNERABLE"
    elif score >= 20:
        resilience_label = "FRAGILE"
    else:
        resilience_label = "CRITICAL"

    # ── Decision Adjustments ──
    # Based on simulation results, what should change in the financial plan?
    adjustments = []

    # Check worst-case scenario
    zero_3mo = scenarios["zero_income_3mo"]
    zero_6mo = scenarios["zero_income_6mo"]
    drop_50 = scenarios["income_drop_50"]
    perm_cut = scenarios["permanent_30_cut"]

    if not zero_3mo["survives_full_duration"]:
        adjustments.append({
            "priority": "CRITICAL",
            "action": "BUILD_EMERGENCY_FUND",
            "detail": f"Cannot survive 3 months without income. Need INR {zero_3mo['total_drain'] - total_liquid_savings:,} more in liquid savings.",
            "impact": "Pause all investments until 3-month buffer is built",
        })

    if zero_3mo["survives_full_duration"] and not zero_6mo["survives_full_duration"]:
        adjustments.append({
            "priority": "HIGH",
            "action": "EXTEND_EMERGENCY_FUND",
            "detail": f"Survives 3 months but not 6. Buffer runs out at {zero_6mo['months_buffer_lasts']:.1f} months.",
            "impact": "Allocate 30% of monthly savings to emergency fund until 6-month buffer reached",
        })

    if not drop_50["survives_full_duration"]:
        adjustments.append({
            "priority": "HIGH",
            "action": "REDUCE_FIXED_COSTS",
            "detail": f"A 50% income drop depletes buffer in {drop_50['months_buffer_lasts']:.1f} months.",
            "impact": "Review and reduce fixed expenses. Consider income diversification.",
        })

    if sip_active and sip_amount > 0:
        sip_ratio = sip_amount / salary if salary > 0 else 0
        if score < 40 and sip_ratio > 0.15:
            adjustments.append({
                "priority": "HIGH",
                "action": "REDUCE_SIP",
                "detail": f"SIP at {sip_ratio:.0%} of income while resilience is {resilience_label}.",
                "impact": f"Reduce SIP from INR {sip_amount:,} to INR {int(salary * 0.10):,} until buffer is adequate",
            })

    if perm_cut["recovery_months"] > 12:
        adjustments.append({
            "priority": "MEDIUM",
            "action": "DIVERSIFY_INCOME",
            "detail": f"A permanent 30% pay cut needs {perm_cut['recovery_months']} months recovery.",
            "impact": "Build secondary income streams to reduce single-income dependency",
        })

    # Goal-specific adjustments
    if goals:
        critical_goals_at_risk = []
        for result in scenarios.values():
            for gi in result["goal_impacts"]:
                if gi["feasibility"] in ("AT RISK", "SIGNIFICANT DELAY") and gi["priority"] in ("critical", "high"):
                    if gi["goal_name"] not in [g["goal_name"] for g in critical_goals_at_risk]:
                        critical_goals_at_risk.append(gi)

        if critical_goals_at_risk:
            goal_names = ", ".join(g["goal_name"] for g in critical_goals_at_risk[:3])
            adjustments.append({
                "priority": "HIGH",
                "action": "PROTECT_CRITICAL_GOALS",
                "detail": f"Critical/high goals at risk under shock: {goal_names}",
                "impact": "Increase buffer allocation for these goals or extend timelines",
            })

    if score >= 80 and not adjustments:
        adjustments.append({
            "priority": "INFO",
            "action": "MAINTAIN_COURSE",
            "detail": "Financial plan is resilient across all tested shock scenarios.",
            "impact": "Continue current strategy. Consider optimizing for growth.",
        })

    return {
        "scenarios": scenarios,
        "resilience_score": score,
        "resilience_label": resilience_label,
        "decision_adjustments": adjustments,
    }


def format_shock_simulation(result):
    """Format shock simulation for display output."""
    lines = []

    def indian(n):
        if n < 0:
            return "-" + indian(-n)
        s = str(int(abs(n)))
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

    # Resilience score header
    lines.append(f"  Resilience Score: {result['resilience_score']}/100 ({result['resilience_label']})")
    lines.append("")

    # Scenario results table
    lines.append(f"  {'Scenario':36s} {'Survives?':>10s}  {'Buffer Left':>12s}  {'Recovery':>10s}  {'Severity'}")
    lines.append("  " + "-" * 90)

    for key in ["income_drop_50", "zero_income_3mo", "zero_income_6mo", "permanent_30_cut"]:
        sc = result["scenarios"][key]
        survives = "YES" if sc["survives_full_duration"] else "NO"
        buffer_left = f"INR {indian(sc['buffer_remaining'])}" if sc["survives_full_duration"] else "DEPLETED"
        recovery = f"{sc['recovery_months']}mo" if sc["recovery_months"] > 0 else "---"
        lines.append(f"  {sc['label']:36s} {survives:>10s}  {buffer_left:>12s}  {recovery:>10s}  {sc['severity']}")

    # Goal impact (if any scenario has goal impacts)
    has_goal_impacts = any(sc["goal_impacts"] for sc in result["scenarios"].values())
    if has_goal_impacts:
        lines.append("")
        lines.append("  GOAL IMPACT (worst case: 6mo zero income):")

        worst = result["scenarios"]["zero_income_6mo"]
        if worst["goal_impacts"]:
            lines.append(f"  {'Goal':24s} {'Original SIP':>14s}  {'Post-Shock SIP':>14s}  {'Delay':>8s}  {'Status'}")
            lines.append("  " + "-" * 80)

            for gi in worst["goal_impacts"]:
                orig = f"INR {indian(gi['original_sip'])}/mo"
                new = f"INR {indian(gi['new_sip_needed'])}/mo"
                delay = f"+{gi['delay_months']}mo" if gi["delay_months"] > 0 else "---"
                lines.append(f"  {gi['goal_name']:24s} {orig:>14s}  {new:>14s}  {delay:>8s}  {gi['feasibility']}")

    # Decision Adjustments
    if result["decision_adjustments"]:
        lines.append("")
        lines.append("  DECISION ADJUSTMENTS:")
        for i, adj in enumerate(result["decision_adjustments"], 1):
            lines.append(f"    {i}. [{adj['priority']}] {adj['action']}")
            lines.append(f"       {adj['detail']}")
            lines.append(f"       -> {adj['impact']}")

    return "\n".join(lines)
