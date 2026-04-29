"""
tax_engine.py - Dynamic Tax Engine (Config-Driven)

7-Layer tax system replacing hardcoded rates with modular, policy-aware engine:

  Layer 1: Tax Rule Engine (config-driven, versioned rules)
  Layer 2: User Tax Profile (slab, income type, deductions)
  Layer 3: After-Tax Return Engine (pre-tax -> post-tax per strategy)
  Layer 4: Tax-Aware Decision Logic (slab-based suggestions)
  Layer 5: Policy Change Handling (versioned rule files)
  Layer 6: Tax Impact Simulation (pre vs post-tax comparison)
  Layer 7: Tax Optimization Engine (ELSS, holding period, strategies)

Architecture:
    User Input -> Tax Profile -> After-Tax Returns -> Goal Feasibility
    Tax Rules (versioned) -> Policy-aware adjustments -> Decision Logic

When government changes rules: update config -> system adapts instantly.
No ML. No LLM. Pure rule-based + config-driven.
"""

import json
import os
from pathlib import Path


# ──────────────────────────────────────────────
#  Layer 1: Tax Rule Engine (Config-Driven)
# ──────────────────────────────────────────────

# Default tax rules — Indian FY 2025-26 (AY 2026-27)
# These serve as fallback when no external config is found
DEFAULT_TAX_RULES = {
    "version": "2026",
    "label": "FY 2025-26 (New Regime)",
    "equity": {
        "ltcg_rate": 0.125,           # 12.5% LTCG on equity (Budget 2024)
        "ltcg_exemption": 125000,     # INR 1.25L exempt per year
        "stcg_rate": 0.20,            # 20% STCG on equity (Budget 2024)
        "holding_period_months": 12,  # >12 months = long-term
    },
    "debt": {
        "slab_based": True,           # Taxed at income tax slab rate
        "no_indexation": True,        # Post April 2023: no indexation benefit
        "holding_period_months": 36,  # Was 36mo, now slab-based regardless
    },
    "hybrid": {
        "equity_component_pct": 0.65, # >65% equity = treated as equity fund
        "ltcg_rate": 0.125,           # Same as equity if >65% equity
        "stcg_rate": 0.20,
        "holding_period_months": 12,
    },
    "elss": {
        "section": "80C",
        "deduction_limit": 150000,    # INR 1.5L max deduction
        "lock_in_years": 3,
        "tax_treatment": "equity",    # Taxed like equity (LTCG/STCG)
    },
    "nps": {
        "section": "80CCD(1B)",
        "additional_deduction": 50000,  # Extra INR 50K over 80C
    },
    "income_tax_slabs_new": {
        "regime": "new",
        "slabs": [
            {"upto": 300000,  "rate": 0.00},
            {"upto": 700000,  "rate": 0.05},
            {"upto": 1000000, "rate": 0.10},
            {"upto": 1200000, "rate": 0.15},
            {"upto": 1500000, "rate": 0.20},
            {"upto": 999999999, "rate": 0.30},
        ],
        "rebate_limit": 700000,  # Full rebate if income <= 7L
        "standard_deduction": 75000,
        "cess": 0.04,            # 4% health & education cess
    },
    "income_tax_slabs_old": {
        "regime": "old",
        "slabs": [
            {"upto": 250000,  "rate": 0.00},
            {"upto": 500000,  "rate": 0.05},
            {"upto": 1000000, "rate": 0.20},
            {"upto": 999999999, "rate": 0.30},
        ],
        "rebate_limit": 500000,
        "standard_deduction": 50000,
        "cess": 0.04,
    },
    "surcharge": {
        # Surcharge on income tax (not on capital gains)
        "slabs": [
            {"above": 5000000,  "rate": 0.10},
            {"above": 10000000, "rate": 0.15},
            {"above": 20000000, "rate": 0.25},
            {"above": 50000000, "rate": 0.37},
        ],
    },
    "tds": {
        "dividend_rate": 0.10,       # TDS on dividends > INR 5000
        "dividend_threshold": 5000,
        "interest_rate": 0.10,       # TDS on FD interest > INR 40000
        "interest_threshold": 40000,
    },
}

# Tax rules directory for versioned configs
TAX_RULES_DIR = Path(__file__).resolve().parent.parent / "tax_rules"

_current_rules = None


def load_tax_rules(version=None):
    """
    Load tax rules. Priority:
      1. External file: tax_rules/tax_rules_{version}.json
      2. Latest file in tax_rules/ directory
      3. DEFAULT_TAX_RULES (built-in fallback)

    Returns dict of tax rules.
    """
    global _current_rules

    # Try external config
    if TAX_RULES_DIR.exists():
        if version:
            rule_file = TAX_RULES_DIR / f"tax_rules_{version}.json"
            if rule_file.exists():
                with open(rule_file, "r") as f:
                    _current_rules = json.load(f)
                    return _current_rules

        # Find latest version
        rule_files = sorted(TAX_RULES_DIR.glob("tax_rules_*.json"), reverse=True)
        if rule_files:
            with open(rule_files[0], "r") as f:
                _current_rules = json.load(f)
                return _current_rules

    # Fallback to built-in
    _current_rules = DEFAULT_TAX_RULES
    return _current_rules


def get_current_rules():
    """Get currently loaded tax rules (loads if needed)."""
    if _current_rules is None:
        load_tax_rules()
    return _current_rules


def save_tax_rules(rules, version=None):
    """Save tax rules to external config file."""
    TAX_RULES_DIR.mkdir(parents=True, exist_ok=True)
    ver = version or rules.get("version", "custom")
    path = TAX_RULES_DIR / f"tax_rules_{ver}.json"
    with open(path, "w") as f:
        json.dump(rules, f, indent=2)
    return str(path)


# ──────────────────────────────────────────────
#  Layer 2: User Tax Profile
# ──────────────────────────────────────────────

def compute_user_tax_profile(annual_income, income_type="salaried",
                              regime="new", deductions_80c=0,
                              deductions_80d=0, hra_claimed=0,
                              existing_elss=0):
    """
    Compute user's effective tax profile.

    Args:
        annual_income: int — gross annual income
        income_type: str — salaried / freelance / business / pension
        regime: str — "new" or "old"
        deductions_80c: int — amount claimed under 80C (excl ELSS)
        deductions_80d: int — health insurance (80D)
        hra_claimed: int — HRA exemption (old regime only)
        existing_elss: int — ELSS already invested this year

    Returns dict with:
        tax_slab_pct: float — marginal tax rate
        effective_tax_rate: float — actual % of income going to tax
        total_tax: int — annual tax liability
        remaining_80c: int — how much more can invest under 80C
        taxable_income: int
    """
    rules = get_current_rules()
    slab_key = f"income_tax_slabs_{regime}"
    slab_config = rules.get(slab_key, rules["income_tax_slabs_new"])

    # Standard deduction
    std_deduction = slab_config.get("standard_deduction", 75000)

    # Taxable income
    if regime == "old":
        total_deductions = std_deduction + min(deductions_80c + existing_elss, 150000) + deductions_80d + hra_claimed
    else:
        # New regime: only standard deduction + NPS (limited)
        total_deductions = std_deduction

    taxable_income = max(0, annual_income - total_deductions)

    # Rebate check
    rebate_limit = slab_config.get("rebate_limit", 700000)
    if taxable_income <= rebate_limit:
        return {
            "annual_income": annual_income,
            "regime": regime,
            "taxable_income": taxable_income,
            "tax_slab_pct": 0,
            "effective_tax_rate": 0,
            "total_tax": 0,
            "marginal_rate": 0,
            "remaining_80c": max(0, 150000 - deductions_80c - existing_elss) if regime == "old" else 0,
            "remaining_80d": max(0, 25000 - deductions_80d),
            "cess": 0,
        }

    # Slab-based calculation
    tax = 0
    marginal_rate = 0
    prev_limit = 0

    for slab in slab_config["slabs"]:
        upper = slab["upto"]
        rate = slab["rate"]
        if taxable_income > prev_limit:
            taxable_in_slab = min(taxable_income, upper) - prev_limit
            tax += taxable_in_slab * rate
            if taxable_income <= upper:
                marginal_rate = rate
        prev_limit = upper

    if marginal_rate == 0 and tax > 0:
        marginal_rate = slab_config["slabs"][-1]["rate"]

    # Cess
    cess_rate = slab_config.get("cess", 0.04)
    cess = int(tax * cess_rate)
    total_tax = int(tax + cess)

    effective_rate = round(total_tax / annual_income, 4) if annual_income > 0 else 0

    # 80C remaining
    elss_limit = rules.get("elss", {}).get("deduction_limit", 150000)
    remaining_80c = max(0, elss_limit - deductions_80c - existing_elss) if regime == "old" else 0

    return {
        "annual_income": annual_income,
        "regime": regime,
        "taxable_income": taxable_income,
        "tax_slab_pct": round(marginal_rate * 100, 1),
        "effective_tax_rate": round(effective_rate * 100, 2),
        "total_tax": total_tax,
        "marginal_rate": marginal_rate,
        "remaining_80c": remaining_80c,
        "remaining_80d": max(0, 25000 - deductions_80d),
        "cess": cess,
    }


# ──────────────────────────────────────────────
#  Layer 3: After-Tax Return Engine
# ──────────────────────────────────────────────

# Strategy -> asset class mapping
STRATEGY_ASSET_CLASS = {
    "Liquid":     "debt",
    "Debt":       "debt",
    "Hybrid":     "hybrid",
    "Equity":     "equity",
    "Aggressive": "equity",
}


def compute_after_tax_return(strategy, pre_tax_return, holding_years,
                               marginal_rate=0.30, annual_gain=0):
    """
    Compute after-tax return for a given strategy.

    Args:
        strategy: str — Liquid/Debt/Hybrid/Equity/Aggressive
        pre_tax_return: float — annual return (e.g., 0.12 for 12%)
        holding_years: int — how long held
        marginal_rate: float — user's income tax slab rate (for debt)
        annual_gain: int — estimated annual capital gain (for exemption calc)

    Returns dict with:
        pre_tax_return: float
        tax_rate_applied: float
        after_tax_return: float
        tax_drag_pct: float — how much tax reduces return
        asset_class: str
        holding_type: str — "LTCG" or "STCG"
    """
    rules = get_current_rules()
    asset_class = STRATEGY_ASSET_CLASS.get(strategy, "equity")

    if asset_class == "equity":
        eq_rules = rules["equity"]
        holding_threshold = eq_rules["holding_period_months"]

        if holding_years * 12 >= holding_threshold:
            # LTCG
            base_rate = eq_rules["ltcg_rate"]
            exemption = eq_rules["ltcg_exemption"]
            # Effective rate after exemption
            if annual_gain > 0 and annual_gain <= exemption:
                tax_rate = 0  # Fully exempt
            elif annual_gain > exemption:
                taxable_portion = (annual_gain - exemption) / annual_gain
                tax_rate = base_rate * taxable_portion
            else:
                tax_rate = base_rate
            holding_type = "LTCG"
        else:
            # STCG
            tax_rate = eq_rules["stcg_rate"]
            holding_type = "STCG"

    elif asset_class == "debt":
        # Post April 2023: debt funds taxed at slab rate, no indexation
        tax_rate = marginal_rate
        holding_type = "Slab-Based"

    elif asset_class == "hybrid":
        hyb_rules = rules["hybrid"]
        eq_pct = hyb_rules["equity_component_pct"]

        if eq_pct >= 0.65:
            # Treated as equity
            if holding_years * 12 >= hyb_rules["holding_period_months"]:
                tax_rate = hyb_rules["ltcg_rate"]
                holding_type = "LTCG (Equity-type)"
            else:
                tax_rate = hyb_rules["stcg_rate"]
                holding_type = "STCG (Equity-type)"
        else:
            # Treated as debt
            tax_rate = marginal_rate
            holding_type = "Slab-Based (Debt-type)"
    else:
        tax_rate = marginal_rate
        holding_type = "Slab-Based"

    # Add cess on tax
    cess = rules.get("income_tax_slabs_new", {}).get("cess", 0.04)
    effective_tax_rate = tax_rate * (1 + cess)

    after_tax_return = round(pre_tax_return * (1 - effective_tax_rate), 4)
    tax_drag = round((pre_tax_return - after_tax_return) * 100, 2)

    return {
        "pre_tax_return": pre_tax_return,
        "tax_rate_applied": round(effective_tax_rate, 4),
        "after_tax_return": after_tax_return,
        "tax_drag_pct": tax_drag,
        "asset_class": asset_class,
        "holding_type": holding_type,
        "strategy": strategy,
    }


# ──────────────────────────────────────────────
#  Layer 4: Tax-Aware Decision Logic
# ──────────────────────────────────────────────

def generate_tax_decisions(tax_profile, strategies_used, holding_years_map=None):
    """
    Generate tax-aware investment decisions.

    Args:
        tax_profile: dict from compute_user_tax_profile()
        strategies_used: list of strategy names user is invested in
        holding_years_map: dict {strategy: years_held} or None

    Returns list of decision dicts.
    """
    decisions = []
    rules = get_current_rules()
    slab = tax_profile["tax_slab_pct"]
    remaining_80c = tax_profile.get("remaining_80c", 0)
    regime = tax_profile.get("regime", "new")

    # ELSS suggestion
    if regime == "old" and remaining_80c > 0 and slab > 0:
        tax_saved = int(remaining_80c * tax_profile["marginal_rate"])
        decisions.append({
            "type": "TAX_SAVING",
            "priority": "HIGH",
            "action": "INVEST_IN_ELSS",
            "detail": f"Invest INR {remaining_80c:,} in ELSS to claim full 80C deduction",
            "tax_saved": tax_saved,
            "impact": f"Save INR {tax_saved:,} in tax + get equity exposure with 3yr lock-in",
        })

    # Regime comparison hint
    if regime == "new" and slab >= 20:
        decisions.append({
            "type": "REGIME_CHECK",
            "priority": "MEDIUM",
            "action": "COMPARE_TAX_REGIMES",
            "detail": f"You're in {slab}% slab under new regime. Compare with old regime if you have HRA/80C deductions.",
            "impact": "Old regime may be better if total deductions exceed INR 3.75L",
        })

    # High slab — prioritize tax-efficient instruments
    if slab >= 30:
        decisions.append({
            "type": "TAX_EFFICIENCY",
            "priority": "HIGH",
            "action": "PREFER_EQUITY_OVER_DEBT",
            "detail": f"At {slab}% slab, debt fund returns taxed heavily. Equity LTCG is only 12.5%.",
            "impact": "For goals >3yr, equity funds are significantly more tax-efficient",
        })

    # Holding period warnings
    if holding_years_map:
        for strategy, years_held in holding_years_map.items():
            asset_class = STRATEGY_ASSET_CLASS.get(strategy, "equity")
            if asset_class == "equity" and years_held < 1:
                decisions.append({
                    "type": "HOLDING_PERIOD",
                    "priority": "MEDIUM",
                    "action": "HOLD_FOR_LTCG",
                    "detail": f"{strategy} held for {years_held}yr — selling now attracts 20% STCG",
                    "impact": f"Hold for {12 - int(years_held * 12)} more months to get 12.5% LTCG rate",
                })

    # NPS suggestion for high earners
    if slab >= 20:
        nps_deduction = rules.get("nps", {}).get("additional_deduction", 50000)
        nps_saving = int(nps_deduction * tax_profile["marginal_rate"])
        decisions.append({
            "type": "TAX_SAVING",
            "priority": "MEDIUM",
            "action": "INVEST_IN_NPS",
            "detail": f"Additional INR {nps_deduction:,} deduction under 80CCD(1B)",
            "tax_saved": nps_saving,
            "impact": f"Save INR {nps_saving:,} in tax (separate from 80C limit)",
        })

    # Dividend vs Growth
    if slab >= 20:
        decisions.append({
            "type": "TAX_EFFICIENCY",
            "priority": "LOW",
            "action": "CHOOSE_GROWTH_OVER_DIVIDEND",
            "detail": "Dividends are taxed at slab rate. Growth option defers tax to redemption.",
            "impact": "Growth funds compound better — tax only on exit, not annually",
        })

    return decisions


# ──────────────────────────────────────────────
#  Layer 5: Policy Change Handling (Versioned)
# ──────────────────────────────────────────────

def list_available_versions():
    """List all available tax rule versions."""
    versions = [{"version": DEFAULT_TAX_RULES["version"], "label": DEFAULT_TAX_RULES["label"], "source": "built-in"}]

    if TAX_RULES_DIR.exists():
        for f in sorted(TAX_RULES_DIR.glob("tax_rules_*.json")):
            try:
                with open(f, "r") as fh:
                    data = json.load(fh)
                    versions.append({
                        "version": data.get("version", f.stem),
                        "label": data.get("label", f.stem),
                        "source": str(f),
                    })
            except (json.JSONDecodeError, KeyError):
                pass

    return versions


# ──────────────────────────────────────────────
#  Layer 6: Tax Impact Simulation
# ──────────────────────────────────────────────

def simulate_tax_impact(strategies_with_returns, holding_years, marginal_rate,
                          monthly_sip=0, initial_investment=0):
    """
    Show pre-tax vs post-tax impact for each strategy.

    Args:
        strategies_with_returns: dict {strategy: pre_tax_return}
        holding_years: int
        marginal_rate: float (0-0.30)
        monthly_sip: int — for absolute impact calculation
        initial_investment: int

    Returns dict with per-strategy impact + totals.
    """
    impacts = []
    total_pre_tax_value = 0
    total_post_tax_value = 0

    for strategy, pre_tax_return in strategies_with_returns.items():
        tax_info = compute_after_tax_return(
            strategy, pre_tax_return, holding_years, marginal_rate,
        )

        # Compute absolute values
        r_pre = pre_tax_return / 12
        r_post = tax_info["after_tax_return"] / 12
        n = holding_years * 12

        # FV with pre-tax return
        if r_pre > 0:
            fv_pre = initial_investment * (1 + r_pre) ** n
            if monthly_sip > 0:
                fv_pre += monthly_sip * (((1 + r_pre) ** n - 1) / r_pre) * (1 + r_pre)
        else:
            fv_pre = initial_investment + monthly_sip * n

        # FV with post-tax return
        if r_post > 0:
            fv_post = initial_investment * (1 + r_post) ** n
            if monthly_sip > 0:
                fv_post += monthly_sip * (((1 + r_post) ** n - 1) / r_post) * (1 + r_post)
        else:
            fv_post = initial_investment + monthly_sip * n

        tax_cost = int(fv_pre - fv_post)

        total_pre_tax_value += int(fv_pre)
        total_post_tax_value += int(fv_post)

        impacts.append({
            "strategy": strategy,
            "pre_tax_return": f"{pre_tax_return:.1%}",
            "after_tax_return": f"{tax_info['after_tax_return']:.1%}",
            "tax_drag": f"{tax_info['tax_drag_pct']:.2f}%",
            "holding_type": tax_info["holding_type"],
            "pre_tax_value": int(fv_pre),
            "post_tax_value": int(fv_post),
            "tax_cost": tax_cost,
        })

    total_tax_cost = total_pre_tax_value - total_post_tax_value

    return {
        "impacts": impacts,
        "total_pre_tax_value": total_pre_tax_value,
        "total_post_tax_value": total_post_tax_value,
        "total_tax_cost": total_tax_cost,
        "tax_efficiency": round(total_post_tax_value / total_pre_tax_value * 100, 1) if total_pre_tax_value > 0 else 100,
    }


# ──────────────────────────────────────────────
#  Layer 7: Tax Optimization Engine
# ──────────────────────────────────────────────

def generate_tax_optimizations(tax_profile, goal_strategies, total_investment_value=0):
    """
    Generate tax optimization recommendations.

    Args:
        tax_profile: dict from compute_user_tax_profile()
        goal_strategies: list of {"name", "strategy", "years", "monthly_sip"}
        total_investment_value: int — total portfolio value

    Returns list of optimization suggestions.
    """
    rules = get_current_rules()
    optimizations = []
    slab = tax_profile["tax_slab_pct"]
    regime = tax_profile.get("regime", "new")

    # 1. ELSS optimization
    remaining_80c = tax_profile.get("remaining_80c", 0)
    if regime == "old" and remaining_80c > 0:
        tax_saved = int(remaining_80c * tax_profile["marginal_rate"])
        effective_benefit = round(tax_saved / remaining_80c * 100, 1) if remaining_80c > 0 else 0
        optimizations.append({
            "category": "SECTION_80C",
            "title": f"Invest INR {remaining_80c:,} in ELSS",
            "description": f"You have INR {remaining_80c:,} remaining under Section 80C. "
                           f"ELSS gives equity returns + tax deduction.",
            "tax_saved": tax_saved,
            "effective_benefit": f"{effective_benefit}% instant return via tax saving",
            "action": "Start ELSS SIP or lumpsum before March 31",
        })

    # 2. Holding period optimization
    short_term_equity = [g for g in goal_strategies
                          if g.get("strategy") in ("Equity", "Aggressive", "Hybrid")
                          and g.get("years", 0) >= 1]
    if short_term_equity:
        stcg = rules["equity"]["stcg_rate"]
        ltcg = rules["equity"]["ltcg_rate"]
        saving = round((stcg - ltcg) * 100, 1)
        optimizations.append({
            "category": "HOLDING_PERIOD",
            "title": f"Hold equity >12 months to save {saving}% tax",
            "description": f"STCG = {stcg:.0%} vs LTCG = {ltcg:.1%}. Holding >1yr saves {saving}% on gains.",
            "tax_saved": None,
            "effective_benefit": f"{saving}% lower tax rate",
            "action": "Avoid selling equity holdings within 12 months of purchase",
        })

    # 3. LTCG harvesting
    exemption = rules["equity"]["ltcg_exemption"]
    if total_investment_value > 0:
        optimizations.append({
            "category": "LTCG_HARVESTING",
            "title": f"Book INR {exemption:,} LTCG annually — tax-free",
            "description": f"Equity LTCG up to INR {exemption:,}/year is tax-free. "
                           f"Sell and re-buy to reset cost basis.",
            "tax_saved": int(exemption * rules["equity"]["ltcg_rate"]),
            "effective_benefit": f"Save up to INR {int(exemption * rules['equity']['ltcg_rate']):,}/year",
            "action": "Each March, book LTCG gains up to exemption limit and reinvest",
        })

    # 4. Growth vs Dividend
    if slab >= 20:
        optimizations.append({
            "category": "FUND_OPTION",
            "title": "Choose GROWTH option over DIVIDEND",
            "description": f"At {slab}% slab, dividends are taxed annually at slab rate. "
                           f"Growth option defers tax to redemption — better compounding.",
            "tax_saved": None,
            "effective_benefit": "0.5-1.5% better CAGR over long term",
            "action": "Switch all funds to Growth option. Avoid IDCW/Dividend plans.",
        })

    # 5. Debt fund strategy
    debt_goals = [g for g in goal_strategies if g.get("strategy") in ("Liquid", "Debt")]
    if debt_goals and slab >= 20:
        optimizations.append({
            "category": "DEBT_STRATEGY",
            "title": "Consider FD alternatives for short-term debt",
            "description": f"Debt funds are now taxed at {slab}% slab rate (same as FD). "
                           f"For <3yr goals, FD/RD may be simpler with same tax treatment.",
            "tax_saved": None,
            "effective_benefit": "Simpler tax compliance, same after-tax return",
            "action": "For short-term goals, compare debt fund vs FD after-tax returns",
        })

    # 6. NPS for additional deduction
    if slab >= 20:
        nps_extra = rules.get("nps", {}).get("additional_deduction", 50000)
        nps_saving = int(nps_extra * tax_profile["marginal_rate"])
        optimizations.append({
            "category": "NPS",
            "title": f"INR {nps_extra:,} extra deduction via NPS (80CCD-1B)",
            "description": f"Beyond 80C limit. Saves INR {nps_saving:,} in tax. "
                           f"Partial equity allocation for long-term growth.",
            "tax_saved": nps_saving,
            "effective_benefit": f"INR {nps_saving:,}/year tax saving",
            "action": "Invest in NPS Tier-1 for retirement + tax benefit",
        })

    # 7. Regime switch analysis
    if regime == "new" and slab >= 20:
        optimizations.append({
            "category": "REGIME_ANALYSIS",
            "title": "Compare Old vs New tax regime annually",
            "description": "If you have significant HRA, 80C, 80D, home loan deductions, "
                           "old regime may save more tax.",
            "tax_saved": None,
            "effective_benefit": "Potential 1-3L tax saving depending on deductions",
            "action": "Calculate tax under both regimes before filing ITR",
        })

    return optimizations


# ──────────────────────────────────────────────
#  Full Tax Analysis (All Layers Combined)
# ──────────────────────────────────────────────

def analyze_tax_impact(salary, goals, risk_level="medium", income_type="salaried",
                        regime="new", deductions_80c=0, deductions_80d=0,
                        hra_claimed=0, existing_elss=0):
    """
    Run complete tax analysis across all goals.

    Args:
        salary: int — monthly salary
        goals: list of goal dicts
        risk_level: str
        income_type: str
        regime: str — "new" or "old"
        deductions_80c: int
        deductions_80d: int
        hra_claimed: int
        existing_elss: int

    Returns comprehensive tax analysis.
    """
    from financial_engine.goal_planner import _get_strategy, STRATEGY_RETURNS

    annual_income = salary * 12

    # Layer 2: Tax profile
    tax_profile = compute_user_tax_profile(
        annual_income, income_type, regime,
        deductions_80c, deductions_80d, hra_claimed, existing_elss,
    )

    # Layer 3 + 6: After-tax returns per strategy used
    strategies_used = {}
    goal_strategies = []
    for goal in goals:
        from financial_engine.inflation_engine import _detect_goal_type
        strategy = _get_strategy(goal["years"], risk_level)
        pre_tax = STRATEGY_RETURNS[strategy]
        strategies_used[strategy] = pre_tax
        goal_strategies.append({
            "name": goal["name"],
            "strategy": strategy,
            "years": goal["years"],
            "monthly_sip": 0,  # computed later
        })

    # After-tax returns
    after_tax_returns = {}
    for strategy, pre_tax in strategies_used.items():
        atr = compute_after_tax_return(
            strategy, pre_tax, 5,  # assume 5yr avg holding
            tax_profile["marginal_rate"],
        )
        after_tax_returns[strategy] = atr

    # Tax impact simulation
    tax_impact = simulate_tax_impact(
        strategies_used, 5, tax_profile["marginal_rate"],
        monthly_sip=int(salary * 0.20), initial_investment=0,
    )

    # Layer 4: Tax decisions
    decisions = generate_tax_decisions(tax_profile, list(strategies_used.keys()))

    # Layer 7: Tax optimizations
    optimizations = generate_tax_optimizations(
        tax_profile, goal_strategies,
        total_investment_value=0,
    )

    # Per-goal tax-adjusted view
    goal_tax_views = []
    for goal in goals:
        strategy = _get_strategy(goal["years"], risk_level)
        pre_tax = STRATEGY_RETURNS[strategy]
        atr = compute_after_tax_return(
            strategy, pre_tax, goal["years"],
            tax_profile["marginal_rate"],
        )

        pre_tax_pct = pre_tax
        post_tax_pct = atr["after_tax_return"]
        drag = atr["tax_drag_pct"]

        goal_tax_views.append({
            "goal_name": goal["name"],
            "strategy": strategy,
            "years": goal["years"],
            "pre_tax_return": f"{pre_tax_pct:.1%}",
            "after_tax_return": f"{post_tax_pct:.1%}",
            "tax_drag": f"-{drag:.2f}%",
            "holding_type": atr["holding_type"],
        })

    return {
        "tax_rules_version": get_current_rules().get("version", "default"),
        "tax_profile": tax_profile,
        "after_tax_returns": {k: {
            "pre_tax": f"{v['pre_tax_return']:.1%}",
            "post_tax": f"{v['after_tax_return']:.1%}",
            "drag": f"{v['tax_drag_pct']:.2f}%",
            "type": v["holding_type"],
        } for k, v in after_tax_returns.items()},
        "goal_tax_views": goal_tax_views,
        "tax_impact": tax_impact,
        "decisions": decisions,
        "optimizations": optimizations,
    }


# ──────────────────────────────────────────────
#  Formatter
# ──────────────────────────────────────────────

def format_tax_analysis(result):
    """Format tax analysis for display output."""
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

    tp = result["tax_profile"]
    lines.append(f"  Tax Rules: v{result['tax_rules_version']}  |  Regime: {tp['regime'].upper()}  |  Slab: {tp['tax_slab_pct']}%  |  Effective Rate: {tp['effective_tax_rate']}%")
    lines.append(f"  Annual Income: INR {indian(tp['annual_income'])}  |  Tax: INR {indian(tp['total_tax'])}  |  Taxable: INR {indian(tp['taxable_income'])}")
    lines.append("")

    # Pre-tax vs post-tax per goal
    lines.append(f"  {'Goal':24s} {'Strategy':12s} {'Pre-Tax':>9s}  {'Post-Tax':>9s}  {'Tax Drag':>9s}  {'Type'}")
    lines.append("  " + "-" * 82)

    for gv in result["goal_tax_views"]:
        lines.append(
            f"  {gv['goal_name']:24s} {gv['strategy']:12s} "
            f"{gv['pre_tax_return']:>9s}  {gv['after_tax_return']:>9s}  "
            f"{gv['tax_drag']:>9s}  {gv['holding_type']}"
        )

    # Tax impact
    ti = result["tax_impact"]
    if ti["impacts"]:
        lines.append("")
        lines.append(f"  TAX IMPACT SIMULATION (5yr, INR {indian(ti['total_pre_tax_value'])} pre-tax):")
        lines.append(f"    Pre-tax corpus:   INR {indian(ti['total_pre_tax_value'])}")
        lines.append(f"    Post-tax corpus:  INR {indian(ti['total_post_tax_value'])}")
        lines.append(f"    Tax cost:         INR {indian(ti['total_tax_cost'])}")
        lines.append(f"    Tax efficiency:   {ti['tax_efficiency']}%")

    # Tax decisions
    if result["decisions"]:
        lines.append("")
        lines.append("  TAX-AWARE DECISIONS:")
        for i, d in enumerate(result["decisions"], 1):
            saved_str = f" (saves INR {indian(d['tax_saved'])})" if d.get("tax_saved") else ""
            lines.append(f"    {i}. [{d['priority']}] {d['action']}{saved_str}")
            lines.append(f"       {d['detail']}")

    # Tax optimizations
    if result["optimizations"]:
        lines.append("")
        lines.append("  TAX OPTIMIZATION STRATEGIES:")
        for i, opt in enumerate(result["optimizations"], 1):
            saved_str = f" -> saves INR {indian(opt['tax_saved'])}/yr" if opt.get("tax_saved") else ""
            lines.append(f"    {i}. [{opt['category']}] {opt['title']}{saved_str}")
            lines.append(f"       {opt['description']}")
            lines.append(f"       Action: {opt['action']}")

    return "\n".join(lines)
