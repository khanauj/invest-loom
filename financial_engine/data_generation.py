"""
data_generation.py - Synthetic Financial Dataset Generator (v2)

Generates a balanced, multi-dimensional dataset for predicting financial actions.
Includes holdings, SIP activity, and derived features for context-aware recommendations.
"""

import numpy as np
import pandas as pd


SEED = 42
np.random.seed(SEED)

ACTIONS = [
    "BUY", "SELL", "HOLD",
    "START_SIP", "STOP_SIP", "INCREASE_SIP", "REDUCE_SIP", "CONTINUE_SIP",
    "REBALANCE", "SWITCH_TO_DEBT", "SWITCH_TO_EQUITY",
    "DIVERSIFY_PORTFOLIO", "EMERGENCY_FUND_BUILD",
]

RISK_LEVELS = ["low", "medium", "high"]
EXPERIENCE_LEVELS = ["beginner", "intermediate", "expert"]

FEATURE_SCHEMA = {
    "salary":                {"type": "int",   "min": 20000,  "max": 100000},
    "monthly_savings":       {"type": "int",   "min": 2000,   "max": 50000},
    "goal_years":            {"type": "int",   "min": 1,      "max": 15},
    "risk_level":            {"type": "cat",   "values": RISK_LEVELS},
    "dependents":            {"type": "int",   "min": 0,      "max": 5},
    "investment_experience": {"type": "cat",   "values": EXPERIENCE_LEVELS},
    "emergency_fund_months": {"type": "int",   "min": 0,      "max": 12},
    "debt_to_income":        {"type": "float", "min": 0.0,    "max": 0.6},
    # New: holdings & SIP fields
    "current_equity_value":  {"type": "int",   "min": 0,      "max": 500000},
    "current_debt_value":    {"type": "int",   "min": 0,      "max": 500000},
    "sip_amount":            {"type": "int",   "min": 0,      "max": 25000},
    "sip_active":            {"type": "bool"},
    "num_stocks":            {"type": "int",   "min": 0,      "max": 20},
    "num_mutual_funds":      {"type": "int",   "min": 0,      "max": 15},
}


def generate_raw_features(n: int) -> pd.DataFrame:
    """Generate random feature values within specified ranges."""
    data = {}
    for name, spec in FEATURE_SCHEMA.items():
        if spec["type"] == "int":
            data[name] = np.random.randint(spec["min"], spec["max"] + 1, size=n)
        elif spec["type"] == "float":
            data[name] = np.random.uniform(spec["min"], spec["max"], size=n).round(2)
        elif spec["type"] == "cat":
            data[name] = np.random.choice(spec["values"], size=n)
        elif spec["type"] == "bool":
            data[name] = np.random.choice([True, False], size=n)

    df = pd.DataFrame(data)

    # Ensure sip_amount = 0 when sip_active is False
    df.loc[~df["sip_active"], "sip_amount"] = 0

    # Derived features
    df["portfolio_total"] = df["current_equity_value"] + df["current_debt_value"]
    df["equity_pct"] = np.where(
        df["portfolio_total"] > 0,
        (df["current_equity_value"] / df["portfolio_total"] * 100).round(2),
        0.0,
    )
    df["sip_ratio"] = np.where(
        df["salary"] > 0,
        (df["sip_amount"] / df["salary"]).round(4),
        0.0,
    )
    df["diversification_score"] = df["num_stocks"] + df["num_mutual_funds"]

    return df


def assign_action(row: pd.Series) -> str:
    """
    Assign a financial action label using 3-tier priority system.

    TIER 1 — SAFETY (always first):
      Emergency fund, unaffordable SIP, imminent goal, extreme exposure

    TIER 2 — DEBT / STRUCTURAL:
      Rebalance, reduce over-commitment, switch to debt

    TIER 3 — GROWTH (only if safety is clear):
      SIP actions, buy, diversify, equity switch
    """
    sip_active = bool(row["sip_active"])
    equity_pct = row["equity_pct"]
    savings = row["monthly_savings"]
    goal = row["goal_years"]
    risk = row["risk_level"]
    dependents = row["dependents"]
    emergency = row["emergency_fund_months"]
    sip_ratio = row["sip_ratio"]
    dti = row["debt_to_income"]
    div_score = row["diversification_score"]
    portfolio = row["portfolio_total"]

    # ── TIER 1: SAFETY ──
    if emergency == 0:
        return "EMERGENCY_FUND_BUILD"
    if emergency < 3 and (dependents >= 1 or dti >= 0.35):
        return "EMERGENCY_FUND_BUILD"
    if emergency < 4 and dependents >= 3:
        return "EMERGENCY_FUND_BUILD"
    if sip_active and savings < 3000:
        return "STOP_SIP"
    if goal < 2:
        return "SELL"
    if equity_pct > 80:
        return "REBALANCE"

    # ── TIER 2: DEBT / STRUCTURAL ──
    if dti >= 0.4 and sip_active and sip_ratio > 0.15:
        return "REDUCE_SIP"
    if sip_active and sip_ratio > 0.3 and dependents >= 3:
        return "REDUCE_SIP"
    if risk == "low" and equity_pct > 50 and goal <= 5:
        return "SWITCH_TO_DEBT"

    # ── TIER 3: GROWTH ──
    if sip_active and savings > 15000 and goal > 5:
        return "INCREASE_SIP"
    if sip_active and savings >= 5000 and goal > 3:
        return "CONTINUE_SIP"
    if not sip_active and savings > 10000 and goal > 5:
        return "START_SIP"
    if equity_pct < 30 and risk == "high":
        return "BUY"
    if risk == "high" and equity_pct < 40 and goal > 7:
        return "SWITCH_TO_EQUITY"
    if div_score < 3 and portfolio > 50000:
        return "DIVERSIFY_PORTFOLIO"

    return "HOLD"


def balance_dataset(df: pd.DataFrame, samples_per_class: int = 200) -> pd.DataFrame:
    """
    Balance the dataset so each action class has roughly equal representation.
    Under-represented classes are oversampled; over-represented ones are down-sampled.
    """
    balanced_parts = []
    for action in ACTIONS:
        subset = df[df["action"] == action]
        if len(subset) == 0:
            continue
        resampled = subset.sample(n=samples_per_class, replace=len(subset) < samples_per_class,
                                  random_state=SEED)
        balanced_parts.append(resampled)

    balanced = pd.concat(balanced_parts, ignore_index=True)
    return balanced.sample(frac=1, random_state=SEED).reset_index(drop=True)


def generate_dataset(output_path: str = "financial_dataset.csv") -> pd.DataFrame:
    """Full pipeline: generate features, assign labels, balance, and save."""
    raw = generate_raw_features(n=20000)
    raw["action"] = raw.apply(assign_action, axis=1)

    print("--- Raw label distribution (before balancing) ---")
    print(raw["action"].value_counts())
    print()

    df = balance_dataset(raw, samples_per_class=200)

    print("--- Balanced label distribution ---")
    print(df["action"].value_counts())
    print()

    df.to_csv(output_path, index=False)
    print(f"Dataset saved to {output_path}  ({len(df)} rows, {len(df.columns)} columns)")
    return df
