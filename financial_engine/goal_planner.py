"""
goal_planner.py - Multi-Goal Financial Planner

Takes multiple financial goals with individual timelines and computes:
  1. Per-goal strategy (Liquid/Debt/Hybrid/Equity/Aggressive)
  2. SIP allocation split across goals
  3. Progress tracking (% funded)
  4. Gap analysis with monthly requirement
  5. Priority-based ordering
  6. Inflation-adjusted targets (dynamic, category-specific)

No ML. No LLM. Pure compound interest math + inflation engine.

Usage:
    goals = [
        {"name": "Emergency Fund", "target": 240000, "saved": 180000, "years": 1, "priority": "critical"},
        {"name": "Son's College", "target": 800000, "saved": 200000, "years": 5, "priority": "high"},
    ]
    plan = compute_goal_plan(goals, monthly_savings=20000, risk_level="medium")
"""


from financial_engine.inflation_engine import (
    _detect_goal_type, simulate_inflation_scenarios,
    compute_inflation_risk_score, apply_inflation_buffer,
)

# Lazy imports to avoid circular dependency (market_scenario_engine imports from us)
def _get_market_functions():
    from financial_engine.market_scenario_engine import (
        run_monte_carlo, analyze_sequence_risk, assess_timing_risk,
        compute_market_risk_score,
    )
    return run_monte_carlo, analyze_sequence_risk, assess_timing_risk, compute_market_risk_score


def _get_tax_functions():
    from financial_engine.tax_engine import compute_after_tax_return
    return compute_after_tax_return


# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────

# Expected annual returns by strategy
STRATEGY_RETURNS = {
    "Liquid":     0.05,   # 5% — ultra-safe, <1yr
    "Debt":       0.07,   # 7% — short duration, 1-3yr
    "Hybrid":     0.10,   # 10% — balanced, 3-5yr
    "Equity":     0.12,   # 12% — large/multi cap, 5-10yr
    "Aggressive": 0.15,   # 15% — mid/small cap, 10yr+
}

# Strategy selection based on time horizon
HORIZON_STRATEGY = [
    (1,  "Liquid"),
    (3,  "Debt"),
    (5,  "Hybrid"),
    (10, "Equity"),
    (99, "Aggressive"),
]

# Fund recommendations per strategy
STRATEGY_FUNDS = {
    "Liquid": [
        {"type": "Liquid Fund", "allocation": 100, "return": "4-6% p.a."},
    ],
    "Debt": [
        {"type": "Short Duration Fund", "allocation": 50, "return": "6-7% p.a."},
        {"type": "Corporate Bond Fund", "allocation": 30, "return": "7-8% p.a."},
        {"type": "Gilt Fund", "allocation": 20, "return": "6-8% p.a."},
    ],
    "Hybrid": [
        {"type": "Balanced Advantage Fund", "allocation": 50, "return": "9-11% p.a."},
        {"type": "Aggressive Hybrid Fund", "allocation": 30, "return": "10-12% p.a."},
        {"type": "Corporate Bond Fund", "allocation": 20, "return": "7-8% p.a."},
    ],
    "Equity": [
        {"type": "Large Cap Fund", "allocation": 35, "return": "10-12% p.a."},
        {"type": "Flexi Cap Fund", "allocation": 30, "return": "11-14% p.a."},
        {"type": "Mid Cap Fund", "allocation": 20, "return": "12-15% p.a."},
        {"type": "Index Fund", "allocation": 15, "return": "10-12% p.a."},
    ],
    "Aggressive": [
        {"type": "Mid Cap Fund", "allocation": 30, "return": "12-15% p.a."},
        {"type": "Small Cap Fund", "allocation": 25, "return": "14-18% p.a."},
        {"type": "Flexi Cap Fund", "allocation": 20, "return": "11-14% p.a."},
        {"type": "International Fund", "allocation": 15, "return": "12-16% p.a."},
        {"type": "Index Fund", "allocation": 10, "return": "10-12% p.a."},
    ],
}

# Priority ordering
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Goal type presets (common Indian financial goals)
GOAL_PRESETS = {
    "emergency_fund":     {"label": "Emergency Fund", "typical_years": 1, "priority": "critical"},
    "education":          {"label": "Child's Education", "typical_years": 5, "priority": "high"},
    "wedding":            {"label": "Wedding", "typical_years": 7, "priority": "high"},
    "house":              {"label": "House Down Payment", "typical_years": 10, "priority": "medium"},
    "car":                {"label": "Car Purchase", "typical_years": 3, "priority": "medium"},
    "retirement":         {"label": "Retirement Corpus", "typical_years": 20, "priority": "low"},
    "vacation":           {"label": "Vacation / Travel", "typical_years": 2, "priority": "low"},
    "wealth":             {"label": "Wealth Building", "typical_years": 15, "priority": "low"},
}


# ──────────────────────────────────────────────
#  Math
# ──────────────────────────────────────────────

def _future_value_sip(monthly, rate, years):
    """FV of monthly SIP: M * [((1+r)^n - 1) / r] * (1+r)"""
    if monthly <= 0 or years <= 0:
        return 0
    r = rate / 12
    n = years * 12
    return int(monthly * (((1 + r) ** n - 1) / r) * (1 + r))


def _required_monthly_sip(target, saved, rate, years):
    """How much monthly SIP is needed to reach target from current savings."""
    if years <= 0:
        return max(0, target - saved)

    # Future value of what's already saved (lumpsum compounding)
    r = rate / 12
    n = years * 12
    fv_saved = saved * (1 + r) ** n

    gap = max(0, target - fv_saved)
    if gap <= 0:
        return 0

    # Monthly SIP needed for the gap
    if r == 0:
        return int(gap / n)
    monthly = gap / ((((1 + r) ** n - 1) / r) * (1 + r))
    return max(0, int(monthly))


def _get_strategy(years, risk_level="medium"):
    """Assign investment strategy based on time horizon + risk."""
    for max_years, strategy in HORIZON_STRATEGY:
        if years <= max_years:
            base = strategy
            break

    # Risk adjustment: conservative users get downgraded, aggressive upgraded
    strategies = list(STRATEGY_RETURNS.keys())
    idx = strategies.index(base)

    if risk_level == "low":
        idx = max(0, idx - 1)
    elif risk_level == "high":
        idx = min(len(strategies) - 1, idx + 1)

    return strategies[idx]


# ──────────────────────────────────────────────
#  Main Goal Planner
# ──────────────────────────────────────────────

def compute_goal_plan(goals, monthly_savings, risk_level="medium",
                      marginal_tax_rate=0.0):
    """
    Compute a complete multi-goal financial plan.

    Args:
        goals: list of dicts, each with:
            name: str (goal name)
            target: int (target amount in INR)
            saved: int (amount already saved toward this goal)
            years: int/float (years until goal)
            priority: str (critical/high/medium/low)
        monthly_savings: int (total monthly savings available)
        risk_level: str (low/medium/high) — adjusts strategy per goal
        marginal_tax_rate: float (0-0.30) — user's marginal income tax rate

    Returns dict with:
        goal_plans: list of per-goal plans (inflation + market + tax adjusted)
        sip_allocation: total SIP split
        total_monthly_needed: int
        affordable: bool
        shortfall: int (if total needed > savings)
    """
    # Sort by priority then by years (urgent first)
    sorted_goals = sorted(goals, key=lambda g: (PRIORITY_ORDER.get(g["priority"], 3), g["years"]))

    goal_plans = []
    total_needed = 0

    for goal in sorted_goals:
        name = goal["name"]
        target = goal["target"]
        saved = goal.get("saved", 0)
        years = goal["years"]
        priority = goal.get("priority", "medium")

        # Strategy assignment
        strategy = _get_strategy(years, risk_level)
        pre_tax_return = STRATEGY_RETURNS[strategy]

        # ── Tax-adjusted return ──
        if marginal_tax_rate > 0:
            _compute_atr = _get_tax_functions()
            tax_info = _compute_atr(strategy, pre_tax_return, years, marginal_tax_rate)
            expected_return = tax_info["after_tax_return"]
            tax_drag = tax_info["tax_drag_pct"]
        else:
            expected_return = pre_tax_return
            tax_drag = 0.0

        # ── Inflation-adjusted target ──
        goal_type = _detect_goal_type(name)
        scenarios = simulate_inflation_scenarios(name, target, years, goal_type)
        inf_risk = compute_inflation_risk_score(goal_type, years)
        expected_future = scenarios["expected"]["future_cost"]
        buffer_info = apply_inflation_buffer(expected_future, inf_risk["buffer_pct"])
        inflation_adjusted_target = buffer_info["buffered_cost"]

        # Use inflation-adjusted target for SIP calculation
        effective_target = inflation_adjusted_target

        # Gap and monthly requirement (against inflation-adjusted target)
        gap = max(0, effective_target - saved)
        progress_pct = min(100, round(saved / effective_target * 100, 1)) if effective_target > 0 else 100

        # Monthly SIP needed (with compounding, against inflation-adjusted target)
        monthly_needed = _required_monthly_sip(effective_target, saved, expected_return, years)

        # Projected value if SIP maintained
        projected_from_saved = int(saved * (1 + expected_return / 12) ** (years * 12))
        projected_from_sip = _future_value_sip(monthly_needed, expected_return, years)
        projected_total = projected_from_saved + projected_from_sip

        # Fund recommendations for this goal
        funds = STRATEGY_FUNDS.get(strategy, [])

        # ── Market Risk Simulation ──
        _run_mc, _seq_risk, _timing_risk, _mkt_score = _get_market_functions()
        mc = _run_mc(strategy, years, monthly_needed, saved,
                     effective_target, num_simulations=200)
        seq = _seq_risk(strategy, years, monthly_needed, saved)
        timing = _timing_risk(strategy, years)
        mrisk = _mkt_score(
            mc["success_probability"], seq["sequence_risk"], timing["timing_risk"],
        )

        # Status (against inflation-adjusted target, weighted by success probability)
        if progress_pct >= 100:
            status = "FUNDED"
        elif progress_pct >= 75 and mc["success_probability"] >= 70:
            status = "ON TRACK"
        elif progress_pct >= 40 or mc["success_probability"] >= 60:
            status = "BEHIND"
        else:
            status = "AT RISK"

        total_needed += monthly_needed

        goal_plans.append({
            "name": name,
            "target": target,
            "inflation_adjusted_target": inflation_adjusted_target,
            "inflation_risk_score": inf_risk["score"],
            "inflation_risk_label": inf_risk["label"],
            "inflation_buffer_pct": inf_risk["buffer_pct"],
            "inflation_scenarios": {
                "optimistic": scenarios["optimistic"]["future_cost"],
                "expected": scenarios["expected"]["future_cost"],
                "worst_case": scenarios["worst_case"]["future_cost"],
            },
            "goal_type": goal_type,
            "saved": saved,
            "gap": gap,
            "years": years,
            "priority": priority,
            "strategy": strategy,
            "pre_tax_return": pre_tax_return,
            "expected_return": expected_return,
            "tax_drag": tax_drag,
            "monthly_needed": monthly_needed,
            "progress_pct": progress_pct,
            "projected_total": projected_total,
            "funds": funds,
            "status": status,
            "success_probability": mc["success_probability"],
            "market_risk_score": mrisk["score"],
            "market_risk_label": mrisk["label"],
            "worst_case_value": mc["worst_case"],
            "sequence_risk": seq["sequence_risk"],
            "timing_risk": timing["timing_risk"],
        })

    # Check affordability
    affordable = total_needed <= monthly_savings
    shortfall = max(0, total_needed - monthly_savings)

    # If not affordable, scale down proportionally (priority-weighted)
    if not affordable and total_needed > 0:
        # Critical/high goals get full allocation first
        remaining = monthly_savings
        for gp in goal_plans:
            if gp["priority"] in ("critical", "high"):
                alloc = min(gp["monthly_needed"], remaining)
                gp["allocated_sip"] = alloc
                remaining -= alloc
            else:
                gp["allocated_sip"] = 0

        # Distribute remaining to medium/low goals
        medium_low = [gp for gp in goal_plans if gp["priority"] not in ("critical", "high")]
        total_ml_needed = sum(gp["monthly_needed"] for gp in medium_low)
        for gp in medium_low:
            if total_ml_needed > 0:
                share = gp["monthly_needed"] / total_ml_needed
                gp["allocated_sip"] = int(remaining * share)
            else:
                gp["allocated_sip"] = 0
    else:
        for gp in goal_plans:
            gp["allocated_sip"] = gp["monthly_needed"]

    # Round SIP allocations to nearest 500
    for gp in goal_plans:
        gp["allocated_sip"] = max(0, (gp["allocated_sip"] // 500) * 500)

    return {
        "goal_plans": goal_plans,
        "total_monthly_needed": total_needed,
        "total_allocated": sum(gp["allocated_sip"] for gp in goal_plans),
        "affordable": affordable,
        "shortfall": shortfall,
        "monthly_savings": monthly_savings,
    }


def format_goal_plan(plan):
    """Format goal plan for display output."""
    lines = []
    gps = plan["goal_plans"]

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

    # Goal table (with inflation-adjusted targets)
    lines.append(f"  {'Goal':24s} {'Today':>12s}  {'Adj. Target':>12s}  {'Saved':>12s}  {'Gap':>12s}  {'Time':>5s}  {'Strategy':12s} {'Status'}")
    lines.append("  " + "-" * 118)

    for gp in gps:
        adj_target = gp.get("inflation_adjusted_target", gp["target"])
        lines.append(
            f"  {gp['name']:24s} INR {indian(gp['target']):>9s}  INR {indian(adj_target):>9s}  INR {indian(gp['saved']):>9s}  "
            f"INR {indian(gp['gap']):>9s}  {gp['years']:>3g}yr  {gp['strategy']:12s} {gp['status']}"
        )

    # Inflation risk per goal
    has_inflation = any("inflation_risk_score" in gp for gp in gps)
    if has_inflation:
        lines.append("")
        lines.append("  INFLATION RISK PER GOAL:")
        for gp in gps:
            if "inflation_risk_score" in gp:
                risk_score = gp["inflation_risk_score"]
                risk_label = gp.get("inflation_risk_label", "").upper()
                buf_pct = gp.get("inflation_buffer_pct", 0)
                sc = gp.get("inflation_scenarios", {})
                lines.append(
                    f"    {gp['name']:24s} Risk: {risk_score:3d}/100 ({risk_label:9s})  "
                    f"Buffer: +{buf_pct:.0%}  "
                    f"Range: INR {indian(sc.get('optimistic', 0))} - INR {indian(sc.get('worst_case', 0))}"
                )

    # Tax impact per goal
    has_tax = any(gp.get("tax_drag", 0) > 0 for gp in gps)
    if has_tax:
        lines.append("")
        lines.append("  TAX IMPACT PER GOAL:")
        for gp in gps:
            if gp.get("tax_drag", 0) > 0:
                lines.append(
                    f"    {gp['name']:24s} Pre-tax: {gp['pre_tax_return']:.1%}  "
                    f"Post-tax: {gp['expected_return']:.1%}  "
                    f"Drag: -{gp['tax_drag']:.2f}%"
                )

    # Market risk per goal
    has_market = any("success_probability" in gp for gp in gps)
    if has_market:
        lines.append("")
        lines.append("  MARKET RISK PER GOAL:")
        for gp in gps:
            if "success_probability" in gp:
                sp = gp["success_probability"]
                mrl = gp.get("market_risk_label", "").upper()
                mrs = gp.get("market_risk_score", 0)
                sr = gp.get("sequence_risk", "low").upper()
                tr = gp.get("timing_risk", "low").upper()
                lines.append(
                    f"    {gp['name']:24s} Success: {sp:5.1f}%  "
                    f"Risk: {mrs:3d}/100 ({mrl:9s})  "
                    f"Seq: {sr:8s}  Timing: {tr}"
                )

    # SIP allocation
    lines.append("")
    lines.append("  SIP ALLOCATION PER GOAL:")
    for gp in gps:
        if gp["allocated_sip"] > 0:
            fund_names = ", ".join(f["type"] for f in gp["funds"][:2])
            lines.append(f"    {gp['name']:24s} -> INR {indian(gp['allocated_sip']):>7s}/mo  -> {fund_names}")
        elif gp["status"] == "FUNDED":
            lines.append(f"    {gp['name']:24s} -> ALREADY FUNDED")
        else:
            lines.append(f"    {gp['name']:24s} -> INR 0/mo (budget exhausted)")

    lines.append(f"    {'':24s}    ─────────────")
    lines.append(f"    {'Total SIP':24s} -> INR {indian(plan['total_allocated']):>7s}/mo")

    # Affordability
    if not plan["affordable"]:
        lines.append("")
        lines.append(f"  WARNING: Need INR {indian(plan['total_monthly_needed'])}/mo but only INR {indian(plan['monthly_savings'])}/mo available")
        lines.append(f"  Shortfall: INR {indian(plan['shortfall'])}/mo -- high priority goals funded first")

    # Progress bars
    lines.append("")
    lines.append("  GOAL PROGRESS:")
    for gp in gps:
        pct = gp["progress_pct"]
        filled = int(pct / 5)
        bar = "#" * filled + "." * (20 - filled)
        lines.append(f"    {gp['name']:24s} {bar}  {pct:5.1f}% funded")

    # Per-goal fund breakdown
    lines.append("")
    lines.append("  PER-GOAL FUND RECOMMENDATION:")
    for gp in gps:
        if gp["allocated_sip"] > 0:
            lines.append(f"    {gp['name']} ({gp['strategy']}, {gp['expected_return']:.0%} p.a.):")
            for f in gp["funds"]:
                amt = int(gp["allocated_sip"] * f["allocation"] / 100)
                amt = (amt // 500) * 500 if amt >= 500 else amt
                lines.append(f"      [{f['allocation']:>3d}%] {f['type']:24s} INR {indian(amt):>7s}/mo  {f['return']}")

    return "\n".join(lines)
