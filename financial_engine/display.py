"""
display.py - Unified Report Formatter

Produces the standard 13-section financial report:
  1.  RISK SCORE (with Income Stability detail)
  2.  CASH FLOW BUFFER ENGINE (survival months, liquid reserves)
  3.  INCOME SHOCK SIMULATION (resilience score, scenario analysis)
  4.  SEGMENT (insight only, not input to models)
  5.  PORTFOLIO ANALYSIS
  6.  SMART PREDICTION (with opportunity cost + recommendation)
  7.  HYBRID ENSEMBLE
  8.  FEATURE ANALYSIS (post-tree FPA)
  9.  INFLATION ANALYSIS (scenario-based, risk-scored, buffered)
  10. MARKET RISK ANALYSIS (Monte Carlo, sequence risk, timing risk)
  11. TAX ANALYSIS (after-tax returns, impact, optimization)
  12. GOAL-BASED PLAN (inflation + market + tax adjusted)
  13. INVESTMENT CATEGORIES (filtered options for user)
"""

from financial_engine.risk_scorer import compute_risk_score, INCOME_TYPES
from financial_engine.segmentation import classify_segment, SEGMENT_PROFILES
from financial_engine.cash_flow_buffer import compute_cash_flow_buffer, format_cash_flow_buffer
from financial_engine.income_shock_simulator import simulate_income_shocks, format_shock_simulation
from financial_engine.inflation_engine import analyze_goal_inflation, format_inflation_analysis
from financial_engine.market_scenario_engine import analyze_market_risk, format_market_risk_analysis
from financial_engine.tax_engine import analyze_tax_impact, format_tax_analysis
from financial_engine.portfolio_analyzer import (
    analyze_portfolio, STOCK_SECTORS, STOCK_MARKET_CAP, STOCK_STYLE, STOCK_DIVIDEND,
)
from financial_engine.rule_engine import predict, compute_intensity, ACTION_DESCRIPTIONS
from financial_engine.opportunity_cost import compute_opportunity_cost
from financial_engine.recommendation_engine import get_recommendation
from financial_engine.category_filter import (
    suggest_categories, MF_CATEGORIES, STOCK_CATEGORIES,
    get_mf_subtype_detail, get_stock_subtype_detail,
)
from financial_engine.feature_analysis import analyze_part_features, format_feature_analysis
from financial_engine.goal_planner import compute_goal_plan, format_goal_plan


def _indian_format(n):
    """Format number in Indian notation: 13,94,034 instead of 1,394,034."""
    if n < 0:
        return "-" + _indian_format(-n)
    s = str(int(n))
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    # Group remaining digits in pairs from right
    groups = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    groups.reverse()
    return ",".join(groups) + "," + last3


def format_full_report(profile, sip_info, stocks, mutual_funds, debt_investments,
                       ml_predictions=None, goals=None, income_type="salaried",
                       tax_regime="new", deductions_80c=0, deductions_80d=0,
                       hra_claimed=0, existing_elss=0):
    """
    Generate the full report.

    Args:
        profile: dict with salary, monthly_savings, goal_years, risk_level,
                 dependents, investment_experience, emergency_fund_months, debt_to_income
        sip_info: dict with sip_active, sip_amount
        stocks: list of {"name": str, "value": int}
        mutual_funds: list of {"name": str, "value": int}
        debt_investments: list of {"name": str, "value": int}
        ml_predictions: dict from predictor.predict_single() or None
        goals: list of {"name", "target", "saved", "years", "priority"} or None

    Returns: formatted string
    """
    lines = []

    # ── Compute all data ──
    pa = analyze_portfolio(stocks, mutual_funds, debt_investments)
    derived = pa["derived"]

    user_input = {
        **profile,
        **sip_info,
        "current_equity_value": derived["current_equity_value"],
        "current_debt_value": derived["current_debt_value"],
        "num_stocks": derived["num_stocks"],
        "num_mutual_funds": derived["num_mutual_funds"],
    }

    engine_args = {k: user_input[k] for k in [
        "salary", "monthly_savings", "goal_years", "risk_level",
        "dependents", "investment_experience", "emergency_fund_months",
        "debt_to_income", "current_equity_value", "current_debt_value",
        "sip_amount", "sip_active", "num_stocks", "num_mutual_funds",
    ]}

    risk = compute_risk_score(**engine_args, income_type=income_type)
    seg = classify_segment(**engine_args)
    rule_action, rule_confidence = predict(**engine_args)
    intensity = compute_intensity(rule_action, **engine_args)
    opp_cost = compute_opportunity_cost(rule_action, user_input, intensity["metrics"])
    rec = get_recommendation(rule_action, user_input["risk_level"], user_input["goal_years"])

    bd = risk["breakdown"]
    equity_pct = derived["current_equity_value"] / (derived["current_equity_value"] + derived["current_debt_value"]) * 100 if (derived["current_equity_value"] + derived["current_debt_value"]) > 0 else 0

    # ══════════════════════════════════════════════
    #  SECTION 1: RISK SCORE
    # ══════════════════════════════════════════════
    label = risk["risk_label"].upper().replace("_", " ")
    isd = risk.get("income_stability_detail", {})
    lines.append(f"  1. RISK SCORE -- {risk['risk_score']}/100 ({label})")
    lines.append(f"  Income Stability      {bd['income_stability']['score']:2d}/20   ({bd['income_stability']['detail']})")
    lines.append(f"    Stability: {isd.get('stability_score', 'N/A')}  |  Volatility: {isd.get('volatility', 'N/A')}  |  Type: {isd.get('income_type_label', 'Salaried')}")
    lines.append(f"  Dependency Burden     {bd['dependency_burden']['score']:2d}/20   ({bd['dependency_burden']['detail']})")
    lines.append(f"  Safety Net            {bd['safety_net']['score']:2d}/20   ({bd['safety_net']['detail']})")
    lines.append(f"  Portfolio Volatility  {bd['portfolio_volatility']['score']:2d}/20   ({bd['portfolio_volatility']['detail']})")
    lines.append(f"  Time Horizon          {bd['time_horizon']['score']:2d}/20   ({bd['time_horizon']['detail']})")

    # ══════════════════════════════════════════════
    #  SECTION 2: CASH FLOW BUFFER ENGINE
    # ══════════════════════════════════════════════
    cfb = compute_cash_flow_buffer(**engine_args)
    lines.append("")
    lines.append(f"  2. CASH FLOW BUFFER -- {cfb['survival_months']:.1f} months ({cfb['buffer_rating'].upper()})")
    lines.append(format_cash_flow_buffer(cfb))

    # ══════════════════════════════════════════════
    #  SECTION 3: INCOME SHOCK SIMULATION
    # ══════════════════════════════════════════════
    shock = simulate_income_shocks(**engine_args, goals=goals)
    lines.append("")
    lines.append(f"  3. INCOME SHOCK SIMULATION -- Resilience: {shock['resilience_score']}/100 ({shock['resilience_label']})")
    lines.append(format_shock_simulation(shock))

    # ══════════════════════════════════════════════
    #  SECTION 4: SEGMENT
    # ══════════════════════════════════════════════
    best_seg = seg["segment"]
    best_profile = seg["profile"]
    scores_sorted = list(seg["match_scores"].items())

    lines.append("")
    lines.append(f"  4. SEGMENT -- {best_profile['label']} (score: {scores_sorted[0][1]})")
    lines.append(f"  Traits:   {', '.join(best_profile['traits'])}")
    if len(scores_sorted) >= 3:
        lines.append(f"  Runner-up: {SEGMENT_PROFILES[scores_sorted[1][0]]['label']} ({scores_sorted[1][1]}), {SEGMENT_PROFILES[scores_sorted[2][0]]['label']} ({scores_sorted[2][1]})")
    elif len(scores_sorted) >= 2:
        lines.append(f"  Runner-up: {SEGMENT_PROFILES[scores_sorted[1][0]]['label']} ({scores_sorted[1][1]})")

    # ══════════════════════════════════════════════
    #  SECTION 5: PORTFOLIO ANALYSIS
    # ══════════════════════════════════════════════
    lines.append("")
    lines.append("  5. PORTFOLIO ANALYSIS")
    lines.append("  STOCKS:")

    for s in pa["holdings_summary"]["stocks"]:
        sector = s["sector"]
        cap = s["market_cap"]
        style = s["style"]
        div_str = "Dividend" if s["dividend"] else "No Div"
        if s.get("quantity") is not None and s.get("price") is not None:
            holding_str = f"{int(s['quantity'])} shares @ INR {s['price']:,.2f} = INR {s['value']:>7,}"
        else:
            holding_str = f"INR {s['value']:>7,}"
        lines.append(f"    {s['name']:14s}  {holding_str:40s}  {sector:10s} {cap:10s} {style:8s} {div_str}")

    # Classification
    sc = pa["stock_classification"]
    large = sc["by_market_cap"]["large_cap"]["count"]
    mid = sc["by_market_cap"]["mid_cap"]["count"]
    small = sc["by_market_cap"]["small_cap"]["count"]
    lines.append("")
    lines.append(f"  Classification: {large} Large Cap | {mid} Mid Cap | {small} Small Cap")

    st = sc["by_style"]
    div_info = sc["by_dividend"]
    total_stocks = len(stocks)
    if div_info["dividend_stocks"] == total_stocks:
        div_text = f"All {total_stocks} pay dividends"
    else:
        div_text = f"{div_info['dividend_stocks']} of {total_stocks} pay dividends"
    lines.append(f"  Style: {st['growth']} Growth + {st['value']} Value + {st['blend']} Blend | {div_text}")

    # Sector Exposure
    lines.append("")
    lines.append("  SECTOR EXPOSURE:")

    # Build sector concentration lookup
    conc_lookup = {}
    for c in pa["concentration"]:
        sec = c.get("sector", "")
        if c["severity"] == "critical":
            conc_lookup[sec] = "CRITICAL"
        elif c["severity"] == "high" and sec not in conc_lookup:
            conc_lookup[sec] = "HIGH"

    # Count stocks per sector
    sector_stock_counts = {}
    for s in stocks:
        sec = STOCK_SECTORS.get(s["name"], "Unknown")
        sector_stock_counts[sec] = sector_stock_counts.get(sec, 0) + 1

    for sec, data in pa["sector_exposure"].items():
        pct = data["percentage"]
        severity = conc_lookup.get(sec, "")
        suffix = ""
        if severity:
            count = sector_stock_counts.get(sec, 0)
            if count >= 2:
                suffix = f"   {severity} -- {count} stocks concentrated"
            else:
                suffix = f"   {severity}"
        lines.append(f"    {sec:14s} {pct:5.1f}%{suffix}")

    # Gaps
    gaps = pa["gaps"]
    missing_cats = [g["category"] for g in gaps["missing_fund_categories"]]
    missing_secs = sorted(gaps.get("missing_sectors", []))

    if missing_cats or missing_secs:
        lines.append("")
        if missing_cats:
            gap_str = ", No ".join(missing_cats)
            lines.append(f"  GAPS: No {gap_str}")
        if missing_secs:
            prefix = "        " if missing_cats else "  GAPS: "
            lines.append(f"{prefix}Missing sectors: {', '.join(missing_secs)}")

    # ══════════════════════════════════════════════
    #  SECTION 6: SMART PREDICTION
    # ══════════════════════════════════════════════
    lines.append("")
    lines.append("  6. SMART PREDICTION")
    lines.append(f"  ACTION:      {rule_action}")
    lines.append(f"  DETAIL:      {intensity['action_detail']}")
    lines.append(f"  CONFIDENCE:  {rule_confidence}%")

    # Opportunity cost with Indian number format
    cost_text = opp_cost["cost_of_inaction"]
    nudge_text = opp_cost["nudge"]

    # Convert numbers in opportunity cost to Indian format
    import re
    def _to_indian(match):
        num = int(match.group(1).replace(",", ""))
        return "INR " + _indian_format(num)

    cost_text = re.sub(r'INR ([\d,]+)', _to_indian, cost_text)
    nudge_text = re.sub(r'INR ([\d,]+)', _to_indian, nudge_text)

    lines.append("")
    lines.append("  OPPORTUNITY COST:")
    lines.append(f'    "{cost_text}"')
    lines.append(f'    "{nudge_text}"')

    # Recommendation
    lines.append("")
    lines.append(f"  RECOMMENDATION: {rec['category_label']}")
    for ft in rec["fund_types"]:
        lines.append(f"    [{ft['allocation']:>3s}] {ft['type']:22s} {ft['expected_return']}")

    # Suggestions
    suggestions = []
    for c in pa["concentration"]:
        if c["severity"] in ("critical", "high"):
            suggestions.append(f"Reduce {c['sector']} exposure ({c['percentage']}%)")
    for g in gaps["missing_fund_categories"]:
        if g["type"] == "equity":
            suggestions.append(f"Add {g['category']} fund")
    if missing_secs:
        suggestions.append(f"Add {', '.join(missing_secs)} sector exposure")

    if suggestions:
        lines.append("")
        lines.append("  SUGGESTIONS:")
        for i, s in enumerate(suggestions, 1):
            lines.append(f"    {i}. {s}")

    # ══════════════════════════════════════════════
    #  SECTION 7: HYBRID ENSEMBLE (PART + Rule Engine)
    # ══════════════════════════════════════════════
    if ml_predictions and "PART" in ml_predictions:
        weights = {
            "PART": 0.55,
            "Rule Engine": 0.45,
        }

        actions = {
            "PART": ml_predictions["PART"],
            "Rule Engine": rule_action,
        }

        # Confidence
        def _ml_conf(model_action):
            if model_action == rule_action:
                return 100
            return 70 if model_action != "HOLD" else 60

        confidences = {
            "PART": _ml_conf(actions["PART"]),
            "Rule Engine": rule_confidence,
        }

        # Weighted scores
        action_scores = {}
        for model, action in actions.items():
            w = weights[model]
            c = confidences[model] / 100
            score = w * c
            action_scores.setdefault(action, 0.0)
            action_scores[action] += score

        winner = max(action_scores, key=action_scores.get)
        total_score = sum(action_scores.values())
        winner_pct = int(action_scores[winner] / total_score * 100) if total_score > 0 else 0

        # Agreement
        agree_count = sum(1 for a in actions.values() if a == winner)
        agreement = "full agreement" if agree_count == 2 else "split decision"

        lines.append("")
        lines.append(f"  7. HYBRID ENSEMBLE -- {winner} ({winner_pct}%, {agreement})")

        for model in ["PART", "Rule Engine"]:
            a = actions[model]
            w = weights[model]
            c = confidences[model]
            score = w * (c / 100)
            lines.append(f"  {model:16s} -> {a:20s} {w:.2f} x {c:3d}% = {score:.4f}")

        lines.append("  " + "-" * 57)

        sorted_scores = sorted(action_scores.items(), key=lambda x: x[1], reverse=True)
        score_parts = [f"{a} = {s:.4f}" for a, s in sorted_scores]
        lines.append(f"  {'   vs   '.join(score_parts)}   -> {winner} wins")

    # ══════════════════════════════════════════════
    #  SECTION 8: FEATURE ANALYSIS (post-tree FPA)
    # ══════════════════════════════════════════════
    if ml_predictions and "PART" in ml_predictions:
        part_model = ml_predictions.get("_part_model")
        X_train = ml_predictions.get("_X_train")
        if part_model is not None:
            fpa = analyze_part_features(part_model, X_train)
            lines.append("")
            lines.append(f"  8. {format_feature_analysis(fpa)}")

    # ══════════════════════════════════════════════
    #  SECTION 9: INFLATION ANALYSIS
    # ══════════════════════════════════════════════
    if goals:
        inf_analysis = analyze_goal_inflation(goals)
        lines.append("")
        lines.append(f"  9. INFLATION ANALYSIS -- Portfolio Risk: {inf_analysis['portfolio_inflation_risk']}/100")
        lines.append(format_inflation_analysis(inf_analysis))

    # ══════════════════════════════════════════════
    #  SECTION 10: MARKET RISK ANALYSIS
    # ══════════════════════════════════════════════
    if goals:
        mkt_risk = analyze_market_risk(goals, user_input["monthly_savings"], user_input["risk_level"])
        lines.append("")
        lines.append(f"  10. MARKET RISK ANALYSIS -- Success Rate: {mkt_risk['portfolio_success_rate']}%  |  Risk: {mkt_risk['portfolio_market_risk']}/100")
        lines.append(format_market_risk_analysis(mkt_risk))

    # ══════════════════════════════════════════════
    #  SECTION 11: TAX ANALYSIS
    # ══════════════════════════════════════════════
    if goals:
        tax_result = analyze_tax_impact(
            user_input["salary"], goals, user_input["risk_level"],
            income_type, tax_regime, deductions_80c, deductions_80d,
            hra_claimed, existing_elss,
        )
        tax_slab = tax_result["tax_profile"]["tax_slab_pct"]
        marginal_rate = tax_result["tax_profile"]["marginal_rate"]
        lines.append("")
        lines.append(f"  11. TAX ANALYSIS -- Slab: {tax_slab}%  |  Regime: {tax_regime.upper()}")
        lines.append(format_tax_analysis(tax_result))
    else:
        marginal_rate = 0.0

    # ══════════════════════════════════════════════
    #  SECTION 12: GOAL-BASED PLAN (inflation + market + tax adjusted)
    # ══════════════════════════════════════════════
    if goals:
        goal_plan = compute_goal_plan(goals, user_input["monthly_savings"],
                                       user_input["risk_level"], marginal_rate)
        lines.append("")
        lines.append(f"  12. GOAL-BASED PLAN (Inflation + Market + Tax Adjusted)")
        lines.append(format_goal_plan(goal_plan))

    # ══════════════════════════════════════════════
    #  SECTION 13: INVESTMENT CATEGORIES
    # ══════════════════════════════════════════════
    cat_suggestion = suggest_categories(
        user_input["risk_level"], user_input["goal_years"],
        user_input["investment_experience"],
    )

    lines.append("")
    lines.append(f"  13. INVESTMENT CATEGORIES -- Filtered for {user_input['risk_level'].upper()} risk, {user_input['goal_years']}yr goal, {user_input['investment_experience']}")

    # Recommended MF category
    primary_key = cat_suggestion["primary"]
    primary_cat = MF_CATEGORIES[primary_key]
    lines.append(f"  Primary: {primary_cat['label']} ({primary_cat['risk']} risk, {primary_cat['expected_return']})")
    lines.append(f"  Best for: {primary_cat['best_for']}")

    # Suitable MF sub-types
    lines.append("")
    lines.append("  SUITABLE MUTUAL FUNDS:")
    lines.append(f"  {'Type':28s} {'Risk':14s} {'Return':16s} {'Horizon'}")
    lines.append("  " + "-" * 75)
    for st_name in cat_suggestion["mf_types"]:
        detail = get_mf_subtype_detail(st_name)
        if detail:
            lines.append(f"  {st_name:28s} {detail['risk']:14s} {detail['return']:16s} {detail['horizon']}")

    # Suitable stock types
    if cat_suggestion["stock_types"]:
        lines.append("")
        lines.append("  SUITABLE STOCKS:")
        lines.append(f"  {'Type':30s} {'Risk':14s} {'Return'}")
        lines.append("  " + "-" * 60)
        for st_name in cat_suggestion["stock_types"]:
            detail = get_stock_subtype_detail(st_name)
            if detail:
                lines.append(f"  {st_name:30s} {detail['risk']:14s} {detail['return']}")

    # Avoid
    if cat_suggestion["avoid"]:
        lines.append("")
        lines.append("  AVOID:")
        for item in cat_suggestion["avoid"]:
            lines.append(f"    X  {item}")

    lines.append("")
    lines.append("  All deterministic. Zero LLM. Zero API cost.")

    return "\n".join(lines)
