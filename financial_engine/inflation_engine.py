"""
inflation_engine.py - Dynamic Goal-Based Inflation Engine

3-Layer inflation system replacing static 6% with dynamic, scenario-based analysis:

  Layer 1: Goal-Based Inflation Mapping
    - Category-specific inflation RANGES (not single values)
    - Maps goal types to (low, high) inflation bands

  Layer 2: Scenario Simulation
    - Optimistic (low inflation)
    - Expected (midpoint)
    - Worst Case (high inflation)
    - Computes future cost for each scenario

  Layer 3: Inflation Risk Score (0-100)
    - Based on goal type sensitivity, time horizon, economic volatility
    - Drives buffer % and decision adjustments

  Layer 4: Dynamic Recalibration
    - Year-by-year cost recalculation
    - SIP step-up schedule to track inflation drift

Architecture:
    User Goal -> Goal Inflation Engine -> Scenario Simulation (3 cases)
       -> Inflation Risk Score -> Add Buffer -> Goal Feasibility Engine -> PART Model

No ML. No LLM. No API. Pure math + domain knowledge.
"""


# ──────────────────────────────────────────────
#  Layer 1: Goal-Based Inflation Mapping
# ──────────────────────────────────────────────

# Category -> (low_inflation, high_inflation) annual rates
# Based on Indian economic data and sector-specific trends
GOAL_INFLATION_MAP = {
    "education":      (0.10, 0.14),   # Education inflation 10-14% (tuition, fees)
    "medical":        (0.12, 0.16),   # Medical inflation 12-16% (healthcare costs)
    "wedding":        (0.07, 0.10),   # Wedding inflation 7-10% (venue, services)
    "house":          (0.06, 0.08),   # Real estate inflation 6-8% (property prices)
    "car":            (0.05, 0.07),   # Auto inflation 5-7% (vehicle prices)
    "retirement":     (0.05, 0.07),   # General inflation 5-7% (cost of living)
    "vacation":       (0.06, 0.12),   # Travel inflation 6-12% (highly variable)
    "emergency_fund": (0.05, 0.07),   # General inflation (expense baseline)
    "wealth":         (0.05, 0.07),   # General inflation (benchmark)
    "lifestyle":      (0.06, 0.12),   # Lifestyle inflation 6-12% (discretionary)
    "general":        (0.06, 0.08),   # Default fallback
}

# Goal type sensitivity to inflation (higher = more volatile)
INFLATION_SENSITIVITY = {
    "education":      0.90,   # Very sensitive — regulated + demand-driven
    "medical":        0.95,   # Extremely sensitive — technology + regulation
    "wedding":        0.65,   # Moderately sensitive — some flexibility
    "house":          0.70,   # Sensitive — land scarcity, policy-driven
    "car":            0.40,   # Less sensitive — competition keeps prices
    "retirement":     0.60,   # Moderate — long-term compounding amplifies
    "vacation":       0.50,   # Variable — discretionary, can downgrade
    "emergency_fund": 0.30,   # Low — just tracks general CPI
    "wealth":         0.35,   # Low — benchmark growth target
    "lifestyle":      0.55,   # Moderate — discretionary but sticky
    "general":        0.50,   # Default
}


def _detect_goal_type(goal_name):
    """Detect goal category from goal name string."""
    name_lower = goal_name.lower()
    keywords = {
        "education": ["education", "college", "school", "tuition", "university", "study"],
        "medical": ["medical", "health", "hospital", "surgery", "treatment"],
        "wedding": ["wedding", "marriage", "shaadi"],
        "house": ["house", "home", "flat", "apartment", "property", "down payment", "real estate"],
        "car": ["car", "vehicle", "bike", "auto"],
        "retirement": ["retirement", "retire", "pension", "corpus"],
        "vacation": ["vacation", "travel", "trip", "holiday", "tour"],
        "emergency_fund": ["emergency", "rainy day", "safety net"],
        "wealth": ["wealth", "investment", "grow", "freedom", "fi"],
        "lifestyle": ["lifestyle", "gadget", "phone", "laptop", "upgrade"],
    }
    for category, kws in keywords.items():
        if any(kw in name_lower for kw in kws):
            return category
    return "general"


def get_inflation_range(goal_type):
    """Get (low, high) inflation range for a goal type."""
    return GOAL_INFLATION_MAP.get(goal_type, GOAL_INFLATION_MAP["general"])


def get_expected_inflation(goal_type):
    """Get midpoint expected inflation for a goal type."""
    low, high = get_inflation_range(goal_type)
    return round((low + high) / 2, 4)


# ──────────────────────────────────────────────
#  Layer 2: Scenario Simulation
# ──────────────────────────────────────────────

def _inflate_cost(today_cost, rate, years):
    """Future cost = today_cost * (1 + rate) ^ years"""
    return int(today_cost * (1 + rate) ** years)


def simulate_inflation_scenarios(goal_name, today_cost, years, goal_type=None):
    """
    Simulate 3 inflation scenarios for a single goal.

    Args:
        goal_name: str — name of the goal
        today_cost: int — today's cost in INR
        years: int — years until goal
        goal_type: str or None — if None, auto-detected from goal_name

    Returns dict with:
        goal_name, goal_type, today_cost, years,
        optimistic: {rate, future_cost}
        expected: {rate, future_cost}
        worst_case: {rate, future_cost}
        range_text: "INR X - INR Y"
    """
    if goal_type is None:
        goal_type = _detect_goal_type(goal_name)

    low, high = get_inflation_range(goal_type)
    mid = (low + high) / 2

    optimistic_cost = _inflate_cost(today_cost, low, years)
    expected_cost = _inflate_cost(today_cost, mid, years)
    worst_cost = _inflate_cost(today_cost, high, years)

    return {
        "goal_name": goal_name,
        "goal_type": goal_type,
        "today_cost": today_cost,
        "years": years,
        "optimistic": {
            "label": "Optimistic",
            "inflation_rate": low,
            "future_cost": optimistic_cost,
        },
        "expected": {
            "label": "Expected",
            "inflation_rate": mid,
            "future_cost": expected_cost,
        },
        "worst_case": {
            "label": "Worst Case",
            "inflation_rate": high,
            "future_cost": worst_cost,
        },
        "cost_range": {
            "low": optimistic_cost,
            "high": worst_cost,
        },
    }


# ──────────────────────────────────────────────
#  Layer 3: Inflation Risk Score (0-100)
# ──────────────────────────────────────────────

def compute_inflation_risk_score(goal_type, years):
    """
    Compute inflation risk score (0-100) for a goal.

    Based on:
      1. Goal type sensitivity (0-1) — how volatile is this category?
      2. Time horizon — longer = more uncertainty
      3. Inflation spread — wider range = more risk

    Returns dict with:
        score: int 0-100
        label: str (low / moderate / high / very_high / extreme)
        components: breakdown
        buffer_pct: recommended buffer percentage
    """
    # Component 1: Goal type sensitivity (0-40 pts)
    sensitivity = INFLATION_SENSITIVITY.get(goal_type, 0.50)
    sensitivity_score = int(sensitivity * 40)

    # Component 2: Time horizon risk (0-35 pts)
    # Uncertainty compounds with time
    if years <= 1:
        horizon_score = 5
    elif years <= 3:
        horizon_score = 10
    elif years <= 5:
        horizon_score = 15
    elif years <= 7:
        horizon_score = 20
    elif years <= 10:
        horizon_score = 25
    elif years <= 15:
        horizon_score = 30
    else:
        horizon_score = 35

    # Component 3: Inflation spread risk (0-25 pts)
    low, high = get_inflation_range(goal_type)
    spread = high - low  # e.g., 0.04 for education (10%-14%)
    # Normalize: 0.02 spread = low risk, 0.06+ = very high
    spread_score = min(25, int(spread * 500))  # 0.04 -> 20, 0.06 -> 25

    total = sensitivity_score + horizon_score + spread_score
    total = max(0, min(100, total))

    # Label
    if total <= 25:
        label = "low"
    elif total <= 45:
        label = "moderate"
    elif total <= 65:
        label = "high"
    elif total <= 85:
        label = "very_high"
    else:
        label = "extreme"

    # Buffer recommendation based on risk score
    if total >= 80:
        buffer_pct = 0.25  # 25% buffer
    elif total >= 60:
        buffer_pct = 0.20  # 20% buffer
    elif total >= 40:
        buffer_pct = 0.15  # 15% buffer
    elif total >= 20:
        buffer_pct = 0.10  # 10% buffer
    else:
        buffer_pct = 0.05  # 5% buffer

    return {
        "score": total,
        "label": label,
        "components": {
            "sensitivity": {"score": sensitivity_score, "max": 40, "detail": f"{sensitivity:.0%} category sensitivity"},
            "time_horizon": {"score": horizon_score, "max": 35, "detail": f"{years}yr horizon"},
            "inflation_spread": {"score": spread_score, "max": 25, "detail": f"{low:.0%}-{high:.0%} range ({spread:.0%} spread)"},
        },
        "buffer_pct": buffer_pct,
    }


# ──────────────────────────────────────────────
#  Inflation Buffer
# ──────────────────────────────────────────────

def apply_inflation_buffer(expected_cost, buffer_pct):
    """
    Apply inflation buffer to expected cost.

    Instead of planning for exact INR 31L:
        Plan for INR 31L + 20% = INR 37.2L

    Returns:
        buffered_cost: int
        buffer_amount: int
    """
    buffer_amount = int(expected_cost * buffer_pct)
    buffered_cost = expected_cost + buffer_amount
    return {
        "expected_cost": expected_cost,
        "buffer_pct": buffer_pct,
        "buffer_amount": buffer_amount,
        "buffered_cost": buffered_cost,
    }


# ──────────────────────────────────────────────
#  Layer 4: Dynamic Recalibration
# ──────────────────────────────────────────────

def compute_recalibration_schedule(today_cost, years, goal_type=None, inflation_rate=None):
    """
    Year-by-year cost recalculation showing how goal cost grows.

    This solves "model becomes outdated" — system recalibrates every year.

    Args:
        today_cost: int — today's cost
        years: int — years to goal
        goal_type: str — for inflation rate lookup
        inflation_rate: float — override inflation rate (if None, uses expected)

    Returns:
        schedule: list of {year, cost, yoy_increase}
        total_inflation: float — cumulative inflation over period
        avg_annual_increase: int — average yearly cost increase
    """
    if inflation_rate is None:
        if goal_type:
            inflation_rate = get_expected_inflation(goal_type)
        else:
            inflation_rate = 0.07  # default 7%

    schedule = []
    prev_cost = today_cost

    for year in range(1, years + 1):
        cost = _inflate_cost(today_cost, inflation_rate, year)
        yoy_increase = cost - prev_cost
        schedule.append({
            "year": year,
            "cost": cost,
            "yoy_increase": yoy_increase,
        })
        prev_cost = cost

    final_cost = schedule[-1]["cost"] if schedule else today_cost
    total_inflation = (final_cost - today_cost) / today_cost if today_cost > 0 else 0
    avg_annual_increase = int((final_cost - today_cost) / years) if years > 0 else 0

    return {
        "schedule": schedule,
        "total_inflation": round(total_inflation, 4),
        "avg_annual_increase": avg_annual_increase,
        "inflation_rate_used": inflation_rate,
    }


# ──────────────────────────────────────────────
#  Full Inflation Analysis (All Layers Combined)
# ──────────────────────────────────────────────

def analyze_goal_inflation(goals):
    """
    Run complete inflation analysis for multiple goals.

    Args:
        goals: list of dicts with name, target, saved, years, priority
               (same format as goal_planner)

    Returns dict with:
        goal_analyses: list of per-goal inflation analysis
        portfolio_inflation_risk: weighted average inflation risk
        total_buffer_needed: int
        insights: list of str
    """
    goal_analyses = []
    total_expected = 0
    total_buffered = 0
    risk_sum = 0
    risk_count = 0

    for goal in goals:
        name = goal["name"]
        target = goal["target"]  # today's value
        years = goal["years"]
        saved = goal.get("saved", 0)
        priority = goal.get("priority", "medium")

        # Detect goal type
        goal_type = _detect_goal_type(name)

        # Layer 1 + 2: Scenario simulation
        scenarios = simulate_inflation_scenarios(name, target, years, goal_type)

        # Layer 3: Inflation risk score
        risk = compute_inflation_risk_score(goal_type, years)

        # Inflation buffer
        expected_future = scenarios["expected"]["future_cost"]
        buffer = apply_inflation_buffer(expected_future, risk["buffer_pct"])

        # Layer 4: Recalibration schedule
        recal = compute_recalibration_schedule(target, years, goal_type)

        # Inflation-adjusted target (what to ACTUALLY plan for)
        inflation_adjusted_target = buffer["buffered_cost"]

        # How much more is needed vs original target
        inflation_premium = inflation_adjusted_target - target
        inflation_multiplier = round(inflation_adjusted_target / target, 2) if target > 0 else 1.0

        total_expected += expected_future
        total_buffered += inflation_adjusted_target
        risk_sum += risk["score"]
        risk_count += 1

        goal_analyses.append({
            "goal_name": name,
            "goal_type": goal_type,
            "priority": priority,
            "today_cost": target,
            "years": years,
            "saved": saved,
            "scenarios": scenarios,
            "inflation_risk": risk,
            "buffer": buffer,
            "recalibration": recal,
            "inflation_adjusted_target": inflation_adjusted_target,
            "inflation_premium": inflation_premium,
            "inflation_multiplier": inflation_multiplier,
        })

    # Portfolio-level inflation risk
    portfolio_risk = int(risk_sum / risk_count) if risk_count > 0 else 0
    total_buffer_needed = total_buffered - total_expected

    # Insights
    insights = []

    high_risk_goals = [g for g in goal_analyses if g["inflation_risk"]["score"] >= 60]
    if high_risk_goals:
        names = ", ".join(g["goal_name"] for g in high_risk_goals[:3])
        insights.append(f"HIGH INFLATION RISK: {names} — plan with buffer to avoid shortfall.")

    big_multipliers = [g for g in goal_analyses if g["inflation_multiplier"] >= 2.5]
    if big_multipliers:
        for g in big_multipliers[:2]:
            insights.append(
                f"{g['goal_name']}: Today's INR {g['today_cost']:,} becomes INR {g['inflation_adjusted_target']:,} "
                f"({g['inflation_multiplier']}x in {g['years']}yr)."
            )

    if portfolio_risk >= 60:
        insights.append("Overall portfolio has HIGH inflation exposure. Consider inflation-beating assets (equity, real estate).")
    elif portfolio_risk <= 30:
        insights.append("Overall inflation risk is manageable. Current strategy is adequate.")

    long_goals = [g for g in goal_analyses if g["years"] >= 10]
    if long_goals:
        insights.append("Long-horizon goals need annual SIP step-up of 8-10% to keep pace with inflation.")

    return {
        "goal_analyses": goal_analyses,
        "portfolio_inflation_risk": portfolio_risk,
        "total_expected_cost": total_expected,
        "total_buffered_cost": total_buffered,
        "total_buffer_needed": total_buffer_needed,
        "insights": insights,
    }


# ──────────────────────────────────────────────
#  Formatter
# ──────────────────────────────────────────────

def format_inflation_analysis(result):
    """Format inflation analysis for display output."""
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

    pr = result["portfolio_inflation_risk"]
    if pr >= 60:
        pr_label = "HIGH"
    elif pr >= 40:
        pr_label = "MODERATE"
    else:
        pr_label = "LOW"

    lines.append(f"  Portfolio Inflation Risk: {pr}/100 ({pr_label})")
    lines.append("")

    # Per-goal scenario table
    lines.append(f"  {'Goal':24s} {'Today':>12s}  {'Optimistic':>12s}  {'Expected':>12s}  {'Worst Case':>12s}  {'Risk':>6s}  {'Buffer'}")
    lines.append("  " + "-" * 108)

    for ga in result["goal_analyses"]:
        sc = ga["scenarios"]
        risk = ga["inflation_risk"]
        buf = ga["buffer"]
        lines.append(
            f"  {ga['goal_name']:24s} "
            f"INR {indian(ga['today_cost']):>9s}  "
            f"INR {indian(sc['optimistic']['future_cost']):>9s}  "
            f"INR {indian(sc['expected']['future_cost']):>9s}  "
            f"INR {indian(sc['worst_case']['future_cost']):>9s}  "
            f"{risk['score']:>4d}/100"
            f"  +{buf['buffer_pct']:.0%}"
        )

    # Inflation-adjusted targets
    lines.append("")
    lines.append("  INFLATION-ADJUSTED TARGETS (plan for these, not today's cost):")
    for ga in result["goal_analyses"]:
        multiplier = ga["inflation_multiplier"]
        lines.append(
            f"    {ga['goal_name']:24s} INR {indian(ga['today_cost']):>9s} -> "
            f"INR {indian(ga['inflation_adjusted_target']):>9s}  ({multiplier}x in {ga['years']}yr)"
        )

    # Total buffer
    lines.append("")
    lines.append(f"  Total expected cost (all goals):    INR {indian(result['total_expected_cost'])}")
    lines.append(f"  Total with inflation buffer:        INR {indian(result['total_buffered_cost'])}")
    lines.append(f"  Buffer cushion:                     INR {indian(result['total_buffer_needed'])}")

    # Risk breakdown for highest-risk goal
    highest_risk = max(result["goal_analyses"], key=lambda g: g["inflation_risk"]["score"])
    risk = highest_risk["inflation_risk"]
    lines.append("")
    lines.append(f"  INFLATION RISK BREAKDOWN -- {highest_risk['goal_name']} ({risk['score']}/100, {risk['label'].upper()}):")
    for comp_name, comp in risk["components"].items():
        bar_filled = int(comp["score"] / comp["max"] * 10)
        bar = "#" * bar_filled + "." * (10 - bar_filled)
        lines.append(f"    {comp_name.replace('_', ' ').title():20s} {bar}  {comp['score']:2d}/{comp['max']}   ({comp['detail']})")

    # Dynamic recalibration preview (for highest-risk goal, show first 5 years)
    recal = highest_risk["recalibration"]
    schedule = recal["schedule"][:5]
    if schedule:
        lines.append("")
        lines.append(f"  DYNAMIC RECALIBRATION -- {highest_risk['goal_name']} (year-by-year cost growth):")
        lines.append(f"  {'Year':>6s}  {'Projected Cost':>14s}  {'YoY Increase':>14s}")
        lines.append("  " + "-" * 40)
        for entry in schedule:
            lines.append(
                f"  {'Yr ' + str(entry['year']):>6s}  "
                f"INR {indian(entry['cost']):>10s}  "
                f"+INR {indian(entry['yoy_increase']):>10s}"
            )
        if len(recal["schedule"]) > 5:
            final = recal["schedule"][-1]
            lines.append(f"  {'...':>6s}")
            lines.append(
                f"  {'Yr ' + str(final['year']):>6s}  "
                f"INR {indian(final['cost']):>10s}  "
                f"+INR {indian(final['yoy_increase']):>10s}"
            )
        lines.append(f"  Total inflation: {recal['total_inflation']:.0%} over {len(recal['schedule'])}yr")

    # Insights
    if result["insights"]:
        lines.append("")
        lines.append("  INSIGHTS:")
        for insight in result["insights"]:
            lines.append(f"    -> {insight}")

    return "\n".join(lines)
