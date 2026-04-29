"""
predictor.py - Financial Prediction Engine (PART + Rule Engine)

Runs user profile through PART model and returns prediction.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from financial_engine.model_training import load_models, CATEGORICAL_COLS
from financial_engine.data_generation import FEATURE_SCHEMA, ACTIONS
from financial_engine.rule_engine import ACTION_DESCRIPTIONS
from financial_engine.goal_planner import GOAL_PRESETS


def compute_derived(user_input: dict) -> dict:
    """Compute derived features from raw inputs."""
    extended = dict(user_input)
    equity = extended.get("current_equity_value", 0)
    debt = extended.get("current_debt_value", 0)
    salary = extended.get("salary", 1)
    sip = extended.get("sip_amount", 0)

    extended["portfolio_total"] = equity + debt
    extended["equity_pct"] = round((equity / (equity + debt) * 100), 2) if (equity + debt) > 0 else 0.0
    extended["sip_ratio"] = round(sip / salary, 4) if salary > 0 else 0.0
    extended["diversification_score"] = extended.get("num_stocks", 0) + extended.get("num_mutual_funds", 0)
    # Ensure sip_active is string for model encoding
    extended["sip_active"] = str(extended.get("sip_active", False))
    return extended


def collect_user_input() -> dict:
    """Interactively collect financial profile from user."""
    print("\n" + "=" * 55)
    print("  ENTER YOUR FINANCIAL PROFILE")
    print("=" * 55 + "\n")

    inputs = {}
    inputs["salary"] = _ask_int("Monthly salary (INR)", 20000, 100000)
    inputs["monthly_savings"] = _ask_int("Monthly savings (INR)", 2000, 50000)
    inputs["goal_years"] = _ask_int("Years until financial goal", 1, 15)
    inputs["risk_level"] = _ask_choice("Risk tolerance", ["low", "medium", "high"])
    inputs["dependents"] = _ask_int("Number of dependents", 0, 5)
    inputs["investment_experience"] = _ask_choice("Investment experience", ["beginner", "intermediate", "expert"])
    inputs["emergency_fund_months"] = _ask_int("Emergency fund (months of expenses)", 0, 12)
    inputs["debt_to_income"] = _ask_float("Debt-to-income ratio (0.0 - 0.6)", 0, 0.6)

    print("\n" + "-" * 55)
    print("  CURRENT HOLDINGS & SIP")
    print("-" * 55 + "\n")

    inputs["current_equity_value"] = _ask_int("Current equity value (INR)", 0, 500000)
    inputs["current_debt_value"] = _ask_int("Current debt value (INR)", 0, 500000)
    inputs["sip_active"] = _ask_bool("SIP currently active?")
    inputs["sip_amount"] = _ask_int("SIP amount (INR/month)", 0, 25000) if inputs["sip_active"] else 0
    inputs["num_stocks"] = _ask_int("Number of stocks held", 0, 20)
    inputs["num_mutual_funds"] = _ask_int("Number of mutual funds", 0, 15)

    return inputs


def collect_user_goals() -> list:
    """Interactively collect financial goals from user."""
    print("\n" + "=" * 55)
    print("  YOUR FINANCIAL GOALS")
    print("=" * 55)

    # Show preset options
    presets = list(GOAL_PRESETS.items())
    print("\n  Common goal types:")
    for i, (key, info) in enumerate(presets, 1):
        print(f"    {i}. {info['label']:24s} (typical: {info['typical_years']}yr, {info['priority']} priority)")
    print(f"    {len(presets) + 1}. Custom goal")

    goals = []
    while True:
        print(f"\n  --- Goal {len(goals) + 1} ---")
        choice = _ask_int("Select goal type (number)", 1, len(presets) + 1)

        if choice <= len(presets):
            # Preset goal
            key, info = presets[choice - 1]
            name = info["label"]
            default_years = info["typical_years"]
            default_priority = info["priority"]
            print(f"    Selected: {name}")

            # Let user customize name if they want
            custom = input(f"  Custom name? (Enter to keep '{name}'): ").strip()
            if custom:
                name = custom

            target = _ask_int(f"Target amount for {name} (INR)", 10000, 100000000)
            saved = _ask_int(f"Already saved toward {name} (INR)", 0, target)
            years = _ask_int(f"Years to achieve {name}", 1, 30)
            priority = _ask_choice("Priority", ["critical", "high", "medium", "low"])
        else:
            # Custom goal
            name = input("  Goal name: ").strip()
            if not name:
                name = f"Goal {len(goals) + 1}"
            target = _ask_int(f"Target amount for {name} (INR)", 10000, 100000000)
            saved = _ask_int(f"Already saved toward {name} (INR)", 0, target)
            years = _ask_int(f"Years to achieve {name}", 1, 30)
            priority = _ask_choice("Priority", ["critical", "high", "medium", "low"])

        goals.append({
            "name": name,
            "target": target,
            "saved": saved,
            "years": years,
            "priority": priority,
        })

        print(f"\n    Added: {name} | INR {target:,} | {years}yr | {priority}")

        if len(goals) >= 8:
            print("  (Maximum 8 goals reached)")
            break

        more = input("\n  Add another goal? (y/n): ").strip().lower()
        if more != "y":
            break

    if not goals:
        return []

    # Summary
    print("\n" + "-" * 55)
    print(f"  YOUR {len(goals)} GOALS:")
    print("-" * 55)
    for i, g in enumerate(goals, 1):
        pct = round(g["saved"] / g["target"] * 100, 1) if g["target"] > 0 else 0
        print(f"  {i}. {g['name']:24s} INR {g['target']:>10,}  {g['years']:>2}yr  {g['priority']:8s}  ({pct}% saved)")
    print("-" * 55)

    return goals


def _ask_int(prompt: str, lo: int, hi: int) -> int:
    while True:
        try:
            val = int(input(f"  {prompt} [{lo}-{hi}]: "))
            if lo <= val <= hi:
                return val
            print(f"    Please enter a value between {lo} and {hi}.")
        except ValueError:
            print("    Please enter a valid integer.")


def _ask_float(prompt: str, lo: float, hi: float) -> float:
    while True:
        try:
            val = float(input(f"  {prompt} [{lo}-{hi}]: "))
            if lo <= val <= hi:
                return round(val, 2)
            print(f"    Please enter a value between {lo} and {hi}.")
        except ValueError:
            print("    Please enter a valid number.")


def _ask_choice(prompt: str, choices: list) -> str:
    choices_str = " / ".join(choices)
    while True:
        val = input(f"  {prompt} [{choices_str}]: ").strip().lower()
        if val in choices:
            return val
        print(f"    Please enter one of: {choices_str}")


def _ask_bool(prompt: str) -> bool:
    while True:
        val = input(f"  {prompt} [yes / no]: ").strip().lower()
        if val in ("yes", "y", "true"):
            return True
        if val in ("no", "n", "false"):
            return False
        print("    Enter yes or no.")


def predict_single(user_input: dict, models: dict, data_bundle: dict) -> dict:
    """
    Run a single user profile through PART model.
    Returns dict: model_name -> predicted action label.
    """
    extended = compute_derived(user_input)

    target_enc = data_bundle["target_enc"]
    encoders = data_bundle["encoders"]
    feature_names = data_bundle["feature_names"]
    class_names = list(target_enc.classes_)

    results = {}

    # Encode features for PART
    row_encoded = {}
    for feat in feature_names:
        if feat in encoders:
            row_encoded[feat] = encoders[feat].transform([extended[feat]])[0]
        else:
            row_encoded[feat] = extended[feat]

    X_row = pd.DataFrame([row_encoded])[feature_names]

    # PART prediction
    part_pred_idx = models["PART"].predict(X_row)[0]
    results["PART"] = class_names[part_pred_idx]

    # Pass PART model reference for feature analysis
    results["_part_model"] = models["PART"]
    results["_X_train"] = data_bundle.get("X_train")

    return results


def display_results(user_input: dict, predictions: dict):
    """Pretty-print prediction results."""
    extended = compute_derived(user_input)

    print("\n" + "=" * 55)
    print("  YOUR FINANCIAL PROFILE")
    print("=" * 55)
    for key, val in user_input.items():
        label = key.replace("_", " ").title()
        print(f"  {label:30s}: {val}")

    print(f"\n  --- Derived ---")
    print(f"  {'Portfolio Total':30s}: INR {extended['portfolio_total']:,}")
    print(f"  {'Equity %':30s}: {extended['equity_pct']}%")
    print(f"  {'SIP Ratio':30s}: {extended['sip_ratio']}")
    print(f"  {'Diversification Score':30s}: {extended['diversification_score']}")

    print("\n" + "=" * 55)
    print("  RECOMMENDATIONS")
    print("=" * 55)

    for model_name, action in predictions.items():
        desc = ACTION_DESCRIPTIONS.get(action, "")
        print(f"\n  [{model_name}]")
        print(f"    Action : {action}")
        print(f"    Reason : {desc}")

    print("=" * 55 + "\n")


def run_prediction(model_dir: str = "models"):
    """Full interactive prediction flow."""
    print("Loading trained models...")
    models, data_bundle = load_models(model_dir)
    print("Models loaded.\n")

    while True:
        user_input = collect_user_input()
        goals = collect_user_goals()
        predictions = predict_single(user_input, models, data_bundle)
        display_results(user_input, predictions)

        # Goal-based plan (if goals provided)
        if goals:
            from financial_engine.goal_planner import compute_goal_plan, format_goal_plan
            plan = compute_goal_plan(goals, user_input["monthly_savings"],
                                     user_input.get("risk_level", "medium"))
            print("\n" + "=" * 55)
            print("  GOAL-BASED PLAN")
            print("=" * 55)
            print(format_goal_plan(plan))
            print("=" * 55)

        again = input("\n  Run another prediction? (y/n): ").strip().lower()
        if again != "y":
            print("\n  Goodbye!\n")
            break
