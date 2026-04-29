"""
segmentation.py - Micro-Segmentation Engine

Classifies users into behavioral investor personas based on their
financial profile, risk appetite, and investment patterns.

Segments:
    AGGRESSIVE_INVESTOR   — high risk, high equity, long horizon, experienced
    CONSERVATIVE_SAVER    — low risk, high savings, prefers debt, safety-first
    BALANCED_PLANNER      — moderate everything, diversified, disciplined SIP
    HIGH_RISK_BEGINNER    — high risk tolerance but beginner, under-diversified
    DEBT_HEAVY_STRUGGLER  — high DTI, low savings, needs structural fixes
    YOUNG_ACCUMULATOR     — long horizon, decent savings, building portfolio
    GOAL_CHASER           — short horizon, needs to lock gains and de-risk
    PASSIVE_HOLDER        — stable profile, no active strategy, needs nudge

Each segment has:
    - Behavioral traits
    - Recommended action bias (what actions fit this persona)
    - Warnings (what to watch out for)
"""

from financial_engine.risk_scorer import compute_risk_score


SEGMENT_PROFILES = {
    "AGGRESSIVE_INVESTOR": {
        "label": "Aggressive Investor",
        "icon": "🔥",
        "description": "High conviction, equity-heavy, long-term wealth builder. "
                       "Comfortable with volatility and drawdowns.",
        "traits": ["high risk tolerance", "equity-heavy portfolio", "long horizon", "experienced"],
        "recommended_bias": ["BUY", "SWITCH_TO_EQUITY", "INCREASE_SIP"],
        "warnings": ["Watch equity concentration — diversify beyond 70%",
                      "Don't ignore emergency fund even with high income"],
    },
    "CONSERVATIVE_SAVER": {
        "label": "Conservative Saver",
        "icon": "🛡️",
        "description": "Safety-first approach. Prefers debt instruments, "
                       "strong emergency fund, minimal market exposure.",
        "traits": ["low risk tolerance", "debt-heavy portfolio", "strong emergency fund", "cautious"],
        "recommended_bias": ["CONTINUE_SIP", "SWITCH_TO_DEBT", "HOLD"],
        "warnings": ["May miss growth opportunities by being too conservative",
                      "Consider small equity allocation for inflation protection"],
    },
    "BALANCED_PLANNER": {
        "label": "Balanced Planner",
        "icon": "⚖️",
        "description": "Well-diversified, disciplined SIP investor. "
                       "Good savings habits with moderate risk appetite.",
        "traits": ["moderate risk", "diversified portfolio", "active SIP", "disciplined"],
        "recommended_bias": ["CONTINUE_SIP", "INCREASE_SIP", "DIVERSIFY_PORTFOLIO"],
        "warnings": ["Periodically review asset allocation",
                      "Increase SIP with salary growth"],
    },
    "HIGH_RISK_BEGINNER": {
        "label": "High-Risk Beginner",
        "icon": "⚠️",
        "description": "Wants aggressive returns but lacks experience. "
                       "High ambition meets limited knowledge — needs guidance.",
        "traits": ["high risk tolerance", "beginner", "under-diversified", "overconfident"],
        "recommended_bias": ["DIVERSIFY_PORTFOLIO", "START_SIP", "EMERGENCY_FUND_BUILD"],
        "warnings": ["Risk tolerance doesn't match experience — start small",
                      "Build emergency fund before aggressive investing",
                      "Avoid concentrated bets in individual stocks"],
    },
    "DEBT_HEAVY_STRUGGLER": {
        "label": "Debt-Heavy Struggler",
        "icon": "🏋️",
        "description": "High debt burden eating into capacity. "
                       "Needs to fix fundamentals before investing.",
        "traits": ["high debt-to-income", "low savings ratio", "stressed finances"],
        "recommended_bias": ["EMERGENCY_FUND_BUILD", "STOP_SIP", "REDUCE_SIP"],
        "warnings": ["Priority: reduce debt before investing",
                      "Build 3-month emergency fund minimum",
                      "Avoid new investment commitments until DTI < 30%"],
    },
    "YOUNG_ACCUMULATOR": {
        "label": "Young Accumulator",
        "icon": "🌱",
        "description": "Long runway ahead with decent savings. "
                       "Best phase for compounding — time is the biggest asset.",
        "traits": ["long horizon", "growing savings", "building portfolio", "moderate experience"],
        "recommended_bias": ["START_SIP", "INCREASE_SIP", "BUY", "SWITCH_TO_EQUITY"],
        "warnings": ["Don't delay starting — every year of compounding matters",
                      "Automate investments through SIP"],
    },
    "GOAL_CHASER": {
        "label": "Goal Chaser",
        "icon": "🎯",
        "description": "Goal is within 1-3 years. Time to de-risk, "
                       "lock gains, and shift to safer instruments.",
        "traits": ["short horizon", "needs capital preservation", "de-risking phase"],
        "recommended_bias": ["SELL", "SWITCH_TO_DEBT", "REBALANCE"],
        "warnings": ["Avoid new equity positions with < 3yr horizon",
                      "Lock in gains progressively, not all at once",
                      "Move to liquid/debt funds for goal amount"],
    },
    "PASSIVE_HOLDER": {
        "label": "Passive Holder",
        "icon": "😴",
        "description": "Stable but inactive. Has decent finances but no active strategy. "
                       "Money is sitting idle — needs a nudge to optimize.",
        "traits": ["no SIP", "adequate savings", "no recent portfolio changes", "under-optimized"],
        "recommended_bias": ["START_SIP", "DIVERSIFY_PORTFOLIO", "INCREASE_SIP"],
        "warnings": ["Idle cash loses to inflation — put it to work",
                      "Even a small SIP of 10% salary makes a big difference",
                      "Review portfolio at least quarterly"],
    },
}


def classify_segment(salary, monthly_savings, goal_years, risk_level,
                     dependents, investment_experience, emergency_fund_months,
                     debt_to_income, current_equity_value, current_debt_value,
                     sip_amount, sip_active, num_stocks, num_mutual_funds,
                     income_type="salaried"):
    """
    Classify the user into a micro-segment based on their financial profile.

    Uses a scoring approach — each segment gets points based on how well
    the profile matches its traits. Highest score wins.

    Returns dict with:
        segment: str (segment key)
        profile: dict (full segment profile from SEGMENT_PROFILES)
        match_scores: dict (all segments with their match scores)
    """
    portfolio_total = current_equity_value + current_debt_value
    equity_pct = (current_equity_value / portfolio_total * 100) if portfolio_total > 0 else 0.0
    savings_ratio = monthly_savings / salary if salary > 0 else 0
    sip_ratio = sip_amount / salary if salary > 0 else 0
    diversification = num_stocks + num_mutual_funds

    risk_data = compute_risk_score(
        salary, monthly_savings, goal_years, risk_level,
        dependents, investment_experience, emergency_fund_months,
        debt_to_income, current_equity_value, current_debt_value,
        sip_amount, sip_active, num_stocks, num_mutual_funds,
        income_type,
    )
    risk_score = risk_data["risk_score"]

    scores = {}

    # ── AGGRESSIVE_INVESTOR ──
    s = 0
    if risk_level == "high": s += 25
    if equity_pct > 60: s += 20
    if goal_years > 7: s += 15
    if investment_experience == "expert": s += 20
    elif investment_experience == "intermediate": s += 10
    if savings_ratio > 0.25: s += 10
    if emergency_fund_months >= 6: s += 5
    scores["AGGRESSIVE_INVESTOR"] = s

    # ── CONSERVATIVE_SAVER ──
    s = 0
    if risk_level == "low": s += 25
    if equity_pct < 40: s += 20
    if emergency_fund_months >= 6: s += 20
    if debt_to_income < 0.15: s += 15
    if savings_ratio > 0.3: s += 10
    if diversification >= 5: s += 5
    scores["CONSERVATIVE_SAVER"] = s

    # ── BALANCED_PLANNER ──
    s = 0
    if risk_level == "medium": s += 20
    if 30 <= equity_pct <= 65: s += 15
    if sip_active: s += 20
    if 0.05 <= sip_ratio <= 0.2: s += 10
    if diversification >= 5: s += 15
    if emergency_fund_months >= 4: s += 10
    if debt_to_income < 0.3: s += 5
    scores["BALANCED_PLANNER"] = s

    # ── HIGH_RISK_BEGINNER ──
    s = 0
    if risk_level == "high": s += 25
    if investment_experience == "beginner": s += 30
    if diversification < 4: s += 15
    if emergency_fund_months < 4: s += 10
    if equity_pct > 50: s += 10
    scores["HIGH_RISK_BEGINNER"] = s

    # ── DEBT_HEAVY_STRUGGLER ──
    s = 0
    if debt_to_income >= 0.35: s += 30
    if savings_ratio < 0.15: s += 25
    if emergency_fund_months < 3: s += 20
    if dependents >= 3: s += 15
    if monthly_savings < 5000: s += 10
    scores["DEBT_HEAVY_STRUGGLER"] = s

    # ── YOUNG_ACCUMULATOR ──
    s = 0
    if goal_years >= 8: s += 25
    if savings_ratio >= 0.2: s += 15
    if risk_level in ("medium", "high"): s += 10
    if investment_experience in ("beginner", "intermediate"): s += 10
    if not sip_active and monthly_savings > 8000: s += 15
    if portfolio_total < 200000: s += 10
    if emergency_fund_months >= 3: s += 5
    scores["YOUNG_ACCUMULATOR"] = s

    # ── GOAL_CHASER ──
    s = 0
    if goal_years <= 3: s += 35
    if goal_years <= 2: s += 15
    if equity_pct > 50: s += 15
    if portfolio_total > 100000: s += 10
    if risk_level != "high": s += 10
    scores["GOAL_CHASER"] = s

    # ── PASSIVE_HOLDER ──
    s = 0
    if not sip_active: s += 25
    if monthly_savings > 8000: s += 15
    if emergency_fund_months >= 4: s += 10
    if debt_to_income < 0.25: s += 10
    if diversification < 4: s += 10
    if portfolio_total > 0 and portfolio_total < 300000: s += 10
    if risk_level == "medium": s += 5
    scores["PASSIVE_HOLDER"] = s

    # Winner
    best = max(scores, key=scores.get)

    return {
        "segment": best,
        "profile": SEGMENT_PROFILES[best],
        "match_scores": dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)),
        "risk_score": risk_score,
    }
