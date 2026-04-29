"""
market_scenario_engine.py - Market Uncertainty & Sequence Risk Engine

Replaces static return assumptions with multi-scenario simulation:

  Step 1: Multi-Scenario Returns
    - Bull / Normal / Bear market regimes
    - Strategy-specific return distributions (not one number)

  Step 2: Monte Carlo Simulation (500 runs)
    - Random year-by-year returns from real distributions
    - Captures sequence risk (bad early vs bad late)
    - Produces success probability + percentile outcomes

  Step 3: Sequence Risk Detection
    - Measures impact of crash timing on goal outcomes
    - Early crash penalty vs late crash penalty

  Step 4: Timing Risk
    - Short-horizon goals (<=3yr) get timing risk warnings
    - Recommends de-risking for near-term goals

Output per goal:
    success_probability: float 0-100%
    worst_case_value: int
    expected_value: int
    best_case_value: int
    sequence_risk: str (low / moderate / high)
    timing_risk: str (low / moderate / high)
    market_risk_score: int 0-100
    adjustments: list of recommendations

No ML. No LLM. No API. Pure simulation + statistics.
"""

import random
import math

from financial_engine.goal_planner import STRATEGY_RETURNS, _get_strategy


# ──────────────────────────────────────────────
#  Market Regime Definitions
# ──────────────────────────────────────────────

# Annual return distributions per strategy per market regime
# Each regime has: probability of occurrence, return for each strategy
MARKET_REGIMES = {
    "bull": {
        "label": "Bull Market",
        "probability": 0.30,      # 30% of years historically
        "returns": {
            "Liquid":     0.065,   # Liquid funds track repo rate
            "Debt":       0.09,    # Debt benefits from rate cuts
            "Hybrid":     0.15,    # Equity component rallies
            "Equity":     0.20,    # Strong equity returns
            "Aggressive": 0.28,    # Small/mid caps surge
        },
    },
    "normal": {
        "label": "Normal Market",
        "probability": 0.45,      # 45% of years
        "returns": {
            "Liquid":     0.05,
            "Debt":       0.07,
            "Hybrid":     0.10,
            "Equity":     0.12,
            "Aggressive": 0.15,
        },
    },
    "bear": {
        "label": "Bear Market",
        "probability": 0.15,      # 15% of years
        "returns": {
            "Liquid":     0.04,
            "Debt":       0.05,
            "Hybrid":     -0.05,
            "Equity":     -0.15,
            "Aggressive": -0.25,
        },
    },
    "crash": {
        "label": "Market Crash",
        "probability": 0.05,      # 5% of years (2008, 2020 type)
        "returns": {
            "Liquid":     0.04,
            "Debt":       0.03,
            "Hybrid":     -0.15,
            "Equity":     -0.30,
            "Aggressive": -0.45,
        },
    },
    "stagnation": {
        "label": "Stagnation",
        "probability": 0.05,      # 5% — flat markets
        "returns": {
            "Liquid":     0.04,
            "Debt":       0.055,
            "Hybrid":     0.03,
            "Equity":     0.02,
            "Aggressive": -0.02,
        },
    },
}

# Number of Monte Carlo simulations
DEFAULT_SIMULATIONS = 500


# ──────────────────────────────────────────────
#  Monte Carlo Simulation
# ──────────────────────────────────────────────

def _sample_regime():
    """Sample a random market regime based on probability weights."""
    regimes = list(MARKET_REGIMES.keys())
    weights = [MARKET_REGIMES[r]["probability"] for r in regimes]
    return random.choices(regimes, weights=weights, k=1)[0]


def _simulate_single_path(strategy, years, monthly_sip, initial_savings, seed=None):
    """
    Simulate a single investment path with random market regimes per year.

    Returns:
        final_value: int — portfolio value at end
        yearly_returns: list of float — actual return per year
        yearly_regimes: list of str — regime per year
    """
    if seed is not None:
        random.seed(seed)

    portfolio = float(initial_savings)
    yearly_returns = []
    yearly_regimes = []

    for year in range(years):
        regime = _sample_regime()
        annual_return = MARKET_REGIMES[regime]["returns"].get(strategy, 0.07)

        # Add small random noise (+/- 2%) for realism
        noise = random.gauss(0, 0.02)
        actual_return = annual_return + noise

        yearly_returns.append(round(actual_return, 4))
        yearly_regimes.append(regime)

        # Monthly compounding within the year
        monthly_rate = actual_return / 12
        for month in range(12):
            portfolio = portfolio * (1 + monthly_rate) + monthly_sip

    return {
        "final_value": max(0, int(portfolio)),
        "yearly_returns": yearly_returns,
        "yearly_regimes": yearly_regimes,
    }


def run_monte_carlo(strategy, years, monthly_sip, initial_savings,
                     target, num_simulations=DEFAULT_SIMULATIONS):
    """
    Run full Monte Carlo simulation for a single goal.

    Args:
        strategy: str — investment strategy (Liquid/Debt/Hybrid/Equity/Aggressive)
        years: int — investment horizon
        monthly_sip: int — monthly SIP amount
        initial_savings: int — amount already saved
        target: int — inflation-adjusted target amount
        num_simulations: int — number of paths to simulate

    Returns dict with:
        success_probability: float 0-100
        percentiles: {p10, p25, p50, p75, p90}
        worst_case: int (5th percentile)
        best_case: int (95th percentile)
        expected_value: int (median)
        all_outcomes: sorted list of final values
        scenario_summary: {bull_runs, normal_runs, bear_runs, crash_runs}
    """
    outcomes = []
    regime_counts = {r: 0 for r in MARKET_REGIMES}

    for i in range(num_simulations):
        result = _simulate_single_path(strategy, years, monthly_sip, initial_savings)
        outcomes.append(result["final_value"])
        for regime in result["yearly_regimes"]:
            regime_counts[regime] += 1

    outcomes.sort()

    # Success = final value >= target
    successes = sum(1 for o in outcomes if o >= target)
    success_pct = round(successes / num_simulations * 100, 1)

    # Percentiles
    def percentile(data, p):
        idx = int(len(data) * p / 100)
        idx = max(0, min(len(data) - 1, idx))
        return data[idx]

    p5 = percentile(outcomes, 5)
    p10 = percentile(outcomes, 10)
    p25 = percentile(outcomes, 25)
    p50 = percentile(outcomes, 50)
    p75 = percentile(outcomes, 75)
    p90 = percentile(outcomes, 90)
    p95 = percentile(outcomes, 95)

    # Normalize regime counts to percentages
    total_regime_years = sum(regime_counts.values())
    regime_pcts = {
        r: round(c / total_regime_years * 100, 1) if total_regime_years > 0 else 0
        for r, c in regime_counts.items()
    }

    return {
        "success_probability": success_pct,
        "percentiles": {
            "p5": p5, "p10": p10, "p25": p25,
            "p50": p50, "p75": p75, "p90": p90, "p95": p95,
        },
        "worst_case": p5,
        "best_case": p95,
        "expected_value": p50,
        "mean_value": int(sum(outcomes) / len(outcomes)),
        "target": target,
        "shortfall_at_worst": max(0, target - p5),
        "regime_distribution": regime_pcts,
        "num_simulations": num_simulations,
    }


# ──────────────────────────────────────────────
#  Sequence Risk Analysis
# ──────────────────────────────────────────────

def analyze_sequence_risk(strategy, years, monthly_sip, initial_savings):
    """
    Compare: crash early vs crash late — same average, different outcome.

    Demonstrates why sequence of returns matters.

    Returns dict with:
        crash_early: {returns, final_value}
        crash_late: {returns, final_value}
        sequence_impact_pct: float — how much worse early crash is
        sequence_risk: str — low / moderate / high
    """
    base_return = STRATEGY_RETURNS.get(strategy, 0.10)
    crash_return = -0.25  # A bad year

    # Scenario A: Crash in year 1
    crash_early_returns = [crash_return] + [base_return] * (years - 1)

    # Scenario B: Crash in last year
    crash_late_returns = [base_return] * (years - 1) + [crash_return]

    def simulate_fixed_returns(returns_list, monthly, initial):
        portfolio = float(initial)
        for annual_ret in returns_list:
            monthly_rate = annual_ret / 12
            for _ in range(12):
                portfolio = portfolio * (1 + monthly_rate) + monthly
        return max(0, int(portfolio))

    early_value = simulate_fixed_returns(crash_early_returns, monthly_sip, initial_savings)
    late_value = simulate_fixed_returns(crash_late_returns, monthly_sip, initial_savings)

    # No crash baseline
    no_crash_returns = [base_return] * years
    no_crash_value = simulate_fixed_returns(no_crash_returns, monthly_sip, initial_savings)

    # Impact
    if no_crash_value > 0:
        early_loss_pct = round((no_crash_value - early_value) / no_crash_value * 100, 1)
        late_loss_pct = round((no_crash_value - late_value) / no_crash_value * 100, 1)
    else:
        early_loss_pct = 0
        late_loss_pct = 0

    sequence_impact = round(early_loss_pct - late_loss_pct, 1)

    # Risk level
    if sequence_impact >= 15:
        seq_risk = "high"
    elif sequence_impact >= 8:
        seq_risk = "moderate"
    else:
        seq_risk = "low"

    return {
        "no_crash": {
            "returns": no_crash_returns,
            "final_value": no_crash_value,
        },
        "crash_early": {
            "returns": crash_early_returns,
            "final_value": early_value,
            "loss_from_baseline_pct": early_loss_pct,
        },
        "crash_late": {
            "returns": crash_late_returns,
            "final_value": late_value,
            "loss_from_baseline_pct": late_loss_pct,
        },
        "sequence_impact_pct": sequence_impact,
        "sequence_risk": seq_risk,
        "insight": (
            f"Early crash costs {sequence_impact:.1f}% more than late crash. "
            f"Same average return, different outcome."
        ),
    }


# ──────────────────────────────────────────────
#  Timing Risk Detection
# ──────────────────────────────────────────────

def assess_timing_risk(strategy, years):
    """
    Assess timing risk for a goal based on strategy + horizon.

    Short-horizon + equity-heavy = HIGH timing risk.

    Returns:
        timing_risk: str — low / moderate / high / critical
        detail: str — explanation
        recommendation: str — what to do
    """
    equity_exposure = {
        "Liquid": 0, "Debt": 0, "Hybrid": 0.40,
        "Equity": 0.85, "Aggressive": 1.0,
    }
    eq_pct = equity_exposure.get(strategy, 0.50)

    # Timing risk = f(horizon, equity exposure)
    if years <= 1:
        horizon_factor = 1.0
    elif years <= 2:
        horizon_factor = 0.85
    elif years <= 3:
        horizon_factor = 0.70
    elif years <= 5:
        horizon_factor = 0.40
    elif years <= 7:
        horizon_factor = 0.20
    else:
        horizon_factor = 0.05

    risk_score = eq_pct * horizon_factor

    if risk_score >= 0.60:
        timing_risk = "critical"
        detail = f"Equity exposure {eq_pct:.0%} with only {years}yr horizon — market crash can destroy this goal"
        recommendation = "Move to Debt/Liquid funds immediately. Capital preservation is priority."
    elif risk_score >= 0.35:
        timing_risk = "high"
        detail = f"Significant equity ({eq_pct:.0%}) with short timeline ({years}yr)"
        recommendation = "Reduce equity to <30%. Use Hybrid or Debt allocation."
    elif risk_score >= 0.15:
        timing_risk = "moderate"
        detail = f"Some equity exposure ({eq_pct:.0%}) with {years}yr horizon"
        recommendation = "Consider shifting 20-30% from equity to debt as goal approaches."
    else:
        timing_risk = "low"
        detail = f"Well-matched strategy for {years}yr horizon"
        recommendation = "Continue current allocation. No timing risk concern."

    return {
        "timing_risk": timing_risk,
        "risk_score": round(risk_score, 2),
        "detail": detail,
        "recommendation": recommendation,
    }


# ──────────────────────────────────────────────
#  Market Risk Score (0-100)
# ──────────────────────────────────────────────

def compute_market_risk_score(success_probability, sequence_risk, timing_risk):
    """
    Composite market risk score combining all three dimensions.

    Returns:
        market_risk_score: int 0-100
        label: str
    """
    # Success probability drives 50 points (lower success = higher risk)
    success_component = int((100 - success_probability) * 0.50)

    # Sequence risk drives 25 points
    seq_map = {"low": 5, "moderate": 15, "high": 25}
    seq_component = seq_map.get(sequence_risk, 10)

    # Timing risk drives 25 points
    timing_map = {"low": 3, "moderate": 10, "high": 18, "critical": 25}
    timing_component = timing_map.get(timing_risk, 10)

    total = success_component + seq_component + timing_component
    total = max(0, min(100, total))

    if total <= 20:
        label = "low"
    elif total <= 40:
        label = "moderate"
    elif total <= 60:
        label = "high"
    elif total <= 80:
        label = "very_high"
    else:
        label = "extreme"

    return {
        "score": total,
        "label": label,
        "components": {
            "success_probability": {"score": success_component, "max": 50},
            "sequence_risk": {"score": seq_component, "max": 25},
            "timing_risk": {"score": timing_component, "max": 25},
        },
    }


# ──────────────────────────────────────────────
#  Full Market Risk Analysis (All Goals)
# ──────────────────────────────────────────────

def analyze_market_risk(goals, monthly_savings, risk_level="medium",
                         num_simulations=DEFAULT_SIMULATIONS):
    """
    Run complete market risk analysis for multiple goals.

    For each goal: Monte Carlo simulation + sequence risk + timing risk + market risk score.

    Args:
        goals: list of dicts with name, target, saved, years, priority
        monthly_savings: int — total monthly savings
        risk_level: str — low/medium/high
        num_simulations: int — Monte Carlo paths (default 500)

    Returns dict with:
        goal_analyses: list of per-goal market analysis
        portfolio_success_rate: weighted average success %
        portfolio_market_risk: weighted average market risk score
        decision_adjustments: list of recommendations
    """
    from financial_engine.inflation_engine import (
        _detect_goal_type, simulate_inflation_scenarios,
        compute_inflation_risk_score, apply_inflation_buffer,
    )
    from financial_engine.goal_planner import (
        _get_strategy, _required_monthly_sip, STRATEGY_RETURNS, PRIORITY_ORDER,
    )

    goal_analyses = []
    total_weight = 0
    weighted_success = 0
    weighted_risk = 0

    # Sort and allocate SIP (same logic as goal_planner)
    sorted_goals = sorted(goals, key=lambda g: (PRIORITY_ORDER.get(g.get("priority", "medium"), 3), g["years"]))

    for goal in sorted_goals:
        name = goal["name"]
        target = goal["target"]
        saved = goal.get("saved", 0)
        years = goal["years"]
        priority = goal.get("priority", "medium")

        # Strategy
        strategy = _get_strategy(years, risk_level)
        expected_return = STRATEGY_RETURNS[strategy]

        # Inflation-adjusted target
        goal_type = _detect_goal_type(name)
        scenarios = simulate_inflation_scenarios(name, target, years, goal_type)
        inf_risk = compute_inflation_risk_score(goal_type, years)
        expected_future = scenarios["expected"]["future_cost"]
        buffer_info = apply_inflation_buffer(expected_future, inf_risk["buffer_pct"])
        effective_target = buffer_info["buffered_cost"]

        # SIP needed
        monthly_sip = _required_monthly_sip(effective_target, saved, expected_return, years)

        # ── Monte Carlo ──
        mc = run_monte_carlo(strategy, years, monthly_sip, saved,
                              effective_target, num_simulations)

        # ── Sequence Risk ──
        seq = analyze_sequence_risk(strategy, years, monthly_sip, saved)

        # ── Timing Risk ──
        timing = assess_timing_risk(strategy, years)

        # ── Market Risk Score ──
        mrisk = compute_market_risk_score(
            mc["success_probability"], seq["sequence_risk"], timing["timing_risk"],
        )

        # 3-scenario summary (deterministic, for quick view)
        scenario_returns = {}
        for regime in ["bull", "normal", "bear"]:
            regime_return = MARKET_REGIMES[regime]["returns"].get(strategy, 0.07)
            # Simple FV with this constant return
            r = regime_return / 12
            n = years * 12
            fv_saved = int(saved * (1 + r) ** n)
            fv_sip = int(monthly_sip * (((1 + r) ** n - 1) / r) * (1 + r)) if r > 0 and monthly_sip > 0 else monthly_sip * n
            scenario_returns[regime] = {
                "return": regime_return,
                "projected_value": max(0, fv_saved + fv_sip),
                "meets_target": (fv_saved + fv_sip) >= effective_target,
            }

        # Weight by target size for portfolio-level metrics
        weight = effective_target
        total_weight += weight
        weighted_success += mc["success_probability"] * weight
        weighted_risk += mrisk["score"] * weight

        goal_analyses.append({
            "goal_name": name,
            "goal_type": goal_type,
            "priority": priority,
            "strategy": strategy,
            "years": years,
            "target": effective_target,
            "today_cost": target,
            "monthly_sip": monthly_sip,
            "saved": saved,
            "monte_carlo": mc,
            "sequence_risk": seq,
            "timing_risk": timing,
            "market_risk_score": mrisk,
            "scenario_returns": scenario_returns,
        })

    # Portfolio-level metrics
    portfolio_success = round(weighted_success / total_weight, 1) if total_weight > 0 else 0
    portfolio_risk = int(weighted_risk / total_weight) if total_weight > 0 else 0

    # ── Decision Adjustments ──
    adjustments = []

    for ga in goal_analyses:
        sp = ga["monte_carlo"]["success_probability"]
        tr = ga["timing_risk"]["timing_risk"]
        sr = ga["sequence_risk"]["sequence_risk"]

        if sp < 50:
            adjustments.append({
                "priority": "CRITICAL",
                "goal": ga["goal_name"],
                "action": "INCREASE_SIP_OR_EXTEND",
                "detail": f"Only {sp}% success probability. Goal is likely to fail under market uncertainty.",
                "impact": f"Increase SIP by 30-50% or extend timeline by 2-3 years",
            })
        elif sp < 70:
            adjustments.append({
                "priority": "HIGH",
                "goal": ga["goal_name"],
                "action": "ADD_BUFFER_SIP",
                "detail": f"{sp}% success rate — needs improvement for confidence.",
                "impact": "Add 15-20% extra to monthly SIP as market buffer",
            })

        if tr in ("critical", "high"):
            adjustments.append({
                "priority": "HIGH" if tr == "critical" else "MEDIUM",
                "goal": ga["goal_name"],
                "action": "DE_RISK_ALLOCATION",
                "detail": ga["timing_risk"]["detail"],
                "impact": ga["timing_risk"]["recommendation"],
            })

        if sr == "high" and ga["years"] <= 5:
            adjustments.append({
                "priority": "MEDIUM",
                "goal": ga["goal_name"],
                "action": "HEDGE_SEQUENCE_RISK",
                "detail": f"High sequence risk for {ga['goal_name']} ({ga['years']}yr).",
                "impact": "Split SIP: 60% equity + 40% debt. Gradually shift to debt as goal nears.",
            })

    if portfolio_success >= 80 and not adjustments:
        adjustments.append({
            "priority": "INFO",
            "goal": "Portfolio",
            "action": "MAINTAIN_COURSE",
            "detail": f"Portfolio success rate {portfolio_success}% — well-positioned.",
            "impact": "Continue current strategy. Monitor annually.",
        })

    return {
        "goal_analyses": goal_analyses,
        "portfolio_success_rate": portfolio_success,
        "portfolio_market_risk": portfolio_risk,
        "decision_adjustments": adjustments,
    }


# ──────────────────────────────────────────────
#  Formatter
# ──────────────────────────────────────────────

def format_market_risk_analysis(result):
    """Format market risk analysis for display output."""
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

    ps = result["portfolio_success_rate"]
    pr = result["portfolio_market_risk"]
    if pr >= 60:
        pr_label = "HIGH"
    elif pr >= 40:
        pr_label = "MODERATE"
    else:
        pr_label = "LOW"

    lines.append(f"  Portfolio Success Rate: {ps}%  |  Market Risk: {pr}/100 ({pr_label})")
    lines.append(f"  (Based on {result['goal_analyses'][0]['monte_carlo']['num_simulations']} Monte Carlo simulations per goal)")
    lines.append("")

    # Per-goal success probability
    lines.append(f"  {'Goal':24s} {'Strategy':12s} {'Success':>8s}  {'Worst Case':>12s}  {'Expected':>12s}  {'Best Case':>12s}  {'Market Risk'}")
    lines.append("  " + "-" * 105)

    for ga in result["goal_analyses"]:
        mc = ga["monte_carlo"]
        mrisk = ga["market_risk_score"]
        lines.append(
            f"  {ga['goal_name']:24s} {ga['strategy']:12s} "
            f"{mc['success_probability']:>6.1f}%  "
            f"INR {indian(mc['worst_case']):>9s}  "
            f"INR {indian(mc['expected_value']):>9s}  "
            f"INR {indian(mc['best_case']):>9s}  "
            f"{mrisk['score']:>3d}/100 ({mrisk['label'].upper()})"
        )

    # 3-scenario quick view
    lines.append("")
    lines.append("  SCENARIO ANALYSIS (deterministic):")
    lines.append(f"  {'Goal':24s} {'Bull (14%)':>14s}  {'Normal (10%)':>14s}  {'Bear (4%)':>14s}")
    lines.append("  " + "-" * 72)

    for ga in result["goal_analyses"]:
        sr = ga["scenario_returns"]
        bull_v = sr["bull"]["projected_value"]
        norm_v = sr["normal"]["projected_value"]
        bear_v = sr["bear"]["projected_value"]
        bull_ok = " OK" if sr["bull"]["meets_target"] else " !!"
        norm_ok = " OK" if sr["normal"]["meets_target"] else " !!"
        bear_ok = " OK" if sr["bear"]["meets_target"] else " !!"
        lines.append(
            f"  {ga['goal_name']:24s} "
            f"INR {indian(bull_v):>9s}{bull_ok}  "
            f"INR {indian(norm_v):>9s}{norm_ok}  "
            f"INR {indian(bear_v):>9s}{bear_ok}"
        )

    # Sequence risk
    lines.append("")
    lines.append("  SEQUENCE RISK (crash timing impact):")
    lines.append(f"  {'Goal':24s} {'No Crash':>14s}  {'Crash Early':>14s}  {'Crash Late':>14s}  {'Impact':>8s}  {'Risk'}")
    lines.append("  " + "-" * 95)

    for ga in result["goal_analyses"]:
        seq = ga["sequence_risk"]
        lines.append(
            f"  {ga['goal_name']:24s} "
            f"INR {indian(seq['no_crash']['final_value']):>10s}  "
            f"INR {indian(seq['crash_early']['final_value']):>10s}  "
            f"INR {indian(seq['crash_late']['final_value']):>10s}  "
            f"{seq['sequence_impact_pct']:>+6.1f}%  "
            f"{seq['sequence_risk'].upper()}"
        )

    # Timing risk
    timing_warnings = [ga for ga in result["goal_analyses"] if ga["timing_risk"]["timing_risk"] in ("high", "critical")]
    if timing_warnings:
        lines.append("")
        lines.append("  TIMING RISK WARNINGS:")
        for ga in timing_warnings:
            tr = ga["timing_risk"]
            lines.append(f"    [{tr['timing_risk'].upper()}] {ga['goal_name']}: {tr['detail']}")
            lines.append(f"           -> {tr['recommendation']}")

    # Decision adjustments
    if result["decision_adjustments"]:
        lines.append("")
        lines.append("  DECISION ADJUSTMENTS:")
        for i, adj in enumerate(result["decision_adjustments"], 1):
            lines.append(f"    {i}. [{adj['priority']}] {adj['goal']}: {adj['action']}")
            lines.append(f"       {adj['detail']}")
            lines.append(f"       -> {adj['impact']}")

    return "\n".join(lines)
