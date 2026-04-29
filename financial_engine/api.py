"""
api.py - FastAPI Backend for AI Financial Decision Engine (v2)

Context-aware: accepts holdings, SIP activity, and provides personalized recommendations.

Endpoints:
    POST /predict          Rule-engine prediction (zero ML, fast)
    POST /predict/ml       ML prediction from all 3 models with consensus
    POST /predict/batch    Batch predictions (rule engine)
    GET  /actions          List all possible actions with descriptions
    GET  /models/status    Check which models are loaded
    GET  /health           Health check
    GET  /schema           Input feature schema with valid ranges

Run:
    python main.py api
    uvicorn financial_engine.api:app --reload
"""

import os
import sys
from typing import Optional
from collections import Counter
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# Ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from financial_engine.rule_engine import (
    predict as rule_predict,
    predict_chain as rule_predict_chain,
    compute_intensity,
    ACTION_DESCRIPTIONS,
    VALID_RISK_LEVELS,
    VALID_EXPERIENCE,
)
from financial_engine.risk_scorer import compute_risk_score, INCOME_TYPES
from financial_engine.segmentation import classify_segment, SEGMENT_PROFILES
from financial_engine.cash_flow_buffer import compute_cash_flow_buffer
from financial_engine.income_shock_simulator import simulate_income_shocks
from financial_engine.inflation_engine import (
    analyze_goal_inflation, simulate_inflation_scenarios,
    compute_inflation_risk_score, GOAL_INFLATION_MAP,
)
from financial_engine.market_scenario_engine import (
    analyze_market_risk, run_monte_carlo, analyze_sequence_risk,
    assess_timing_risk, MARKET_REGIMES,
)
from financial_engine.tax_engine import (
    analyze_tax_impact, compute_user_tax_profile, compute_after_tax_return,
    generate_tax_optimizations, generate_tax_decisions,
    get_current_rules, list_available_versions, DEFAULT_TAX_RULES,
)
from financial_engine.opportunity_cost import compute_opportunity_cost
from financial_engine.product_engine import fetch_products_for_action
from financial_engine.recommendation_engine import get_recommendation
from financial_engine.portfolio_analyzer import analyze_portfolio, MF_CATEGORIES

# ML models loaded lazily
_ml_models = None
_ml_data_bundle = None


def _load_ml_models(model_dir="models"):
    global _ml_models, _ml_data_bundle
    if _ml_models is not None:
        return
    try:
        from financial_engine.model_training import load_models
        _ml_models, _ml_data_bundle = load_models(model_dir)
        print(f"ML models loaded from {model_dir}/")
    except Exception as e:
        print(f"Warning: Could not load ML models: {e}")
        print("ML endpoints (/predict/ml) will be unavailable.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models on startup."""
    _load_ml_models()
    yield


app = FastAPI(
    title="AI Financial Decision Engine API v2",
    description="Context-aware ML-powered financial action recommendations. "
                "Understands holdings, SIP activity, and diversification.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
#  Request / Response Models
# ──────────────────────────────────────────────

class FinancialProfile(BaseModel):
    salary: int = Field(..., ge=20000, le=100000, description="Monthly salary (INR)")
    monthly_savings: int = Field(..., ge=2000, le=50000, description="Monthly savings (INR)")
    goal_years: int = Field(..., ge=1, le=15, description="Years to financial goal")
    risk_level: str = Field(..., description="Risk tolerance: low / medium / high")
    dependents: int = Field(..., ge=0, le=5, description="Number of dependents")
    investment_experience: str = Field(..., description="beginner / intermediate / expert")
    emergency_fund_months: int = Field(..., ge=0, le=12, description="Emergency fund (months)")
    debt_to_income: float = Field(..., ge=0, le=0.6, description="Debt-to-income ratio")
    # New: holdings & SIP (optional defaults for backward compatibility)
    current_equity_value: int = Field(0, ge=0, le=500000, description="Current equity holdings (INR)")
    current_debt_value: int = Field(0, ge=0, le=500000, description="Current debt holdings (INR)")
    sip_amount: int = Field(0, ge=0, le=25000, description="Monthly SIP amount (INR)")
    sip_active: bool = Field(False, description="Is SIP currently active?")
    num_stocks: int = Field(0, ge=0, le=20, description="Number of stocks held")
    num_mutual_funds: int = Field(0, ge=0, le=15, description="Number of mutual funds")
    income_type: str = Field("salaried", description="Income type: salaried / freelance / business / mixed / pension")

    @field_validator("risk_level")
    @classmethod
    def validate_risk(cls, v):
        v = v.strip().lower()
        if v not in VALID_RISK_LEVELS:
            raise ValueError(f"Must be one of {VALID_RISK_LEVELS}")
        return v

    @field_validator("investment_experience")
    @classmethod
    def validate_experience(cls, v):
        v = v.strip().lower()
        if v not in VALID_EXPERIENCE:
            raise ValueError(f"Must be one of {VALID_EXPERIENCE}")
        return v

    @field_validator("income_type")
    @classmethod
    def validate_income_type(cls, v):
        v = v.strip().lower()
        valid = set(INCOME_TYPES.keys())
        if v not in valid:
            raise ValueError(f"Must be one of {valid}")
        return v


class Holding(BaseModel):
    name: str
    value: int = Field(..., ge=0)


class DetailedProfile(BaseModel):
    salary: int = Field(..., ge=20000, le=100000)
    monthly_savings: int = Field(..., ge=2000, le=50000)
    goal_years: int = Field(..., ge=1, le=15)
    risk_level: str = Field(...)
    dependents: int = Field(..., ge=0, le=5)
    investment_experience: str = Field(...)
    emergency_fund_months: int = Field(..., ge=0, le=12)
    debt_to_income: float = Field(..., ge=0, le=0.6)
    sip_amount: int = Field(0, ge=0, le=25000)
    sip_active: bool = Field(...)
    income_type: str = Field("salaried")
    stocks: list[Holding] = Field(default_factory=list)
    mutual_funds: list[Holding] = Field(default_factory=list)
    debt_investments: list[Holding] = Field(default_factory=list)

    @field_validator("risk_level")
    @classmethod
    def validate_risk_d(cls, v):
        v = v.strip().lower()
        if v not in VALID_RISK_LEVELS:
            raise ValueError(f"Must be one of {VALID_RISK_LEVELS}")
        return v

    @field_validator("investment_experience")
    @classmethod
    def validate_experience_d(cls, v):
        v = v.strip().lower()
        if v not in VALID_EXPERIENCE:
            raise ValueError(f"Must be one of {VALID_EXPERIENCE}")
        return v

    def to_flat_profile(self, analysis: dict) -> dict:
        """Convert detailed profile + analysis to flat FinancialProfile dict."""
        d = analysis["derived"]
        return {
            "salary": self.salary,
            "monthly_savings": self.monthly_savings,
            "goal_years": self.goal_years,
            "risk_level": self.risk_level,
            "dependents": self.dependents,
            "investment_experience": self.investment_experience,
            "emergency_fund_months": self.emergency_fund_months,
            "debt_to_income": self.debt_to_income,
            "sip_amount": self.sip_amount,
            "sip_active": self.sip_active,
            "current_equity_value": d["current_equity_value"],
            "current_debt_value": d["current_debt_value"],
            "num_stocks": d["num_stocks"],
            "num_mutual_funds": d["num_mutual_funds"],
        }


class PredictionResponse(BaseModel):
    action: str
    action_detail: Optional[str] = None
    description: str
    model: str
    confidence: Optional[str] = None
    intensity: Optional[dict] = None
    opportunity_cost: Optional[dict] = None
    context: Optional[dict] = None


class MLPredictionResponse(BaseModel):
    decision_tree: dict
    ripper: dict
    cn2: dict
    consensus: dict


class BatchRequest(BaseModel):
    profiles: list[FinancialProfile] = Field(..., max_length=100)


class BatchResponse(BaseModel):
    results: list[PredictionResponse]
    count: int


class HybridVoter(BaseModel):
    model: str
    action: str
    weight: float
    model_confidence: str
    weighted_contribution: str


class ConflictInfo(BaseModel):
    has_conflict: bool
    conflict_type: Optional[str] = None  # "rule_vs_ml", "ml_internal", "none"
    rule_engine_overridden: bool
    resolution_method: str


class HybridResponse(BaseModel):
    final_action: str
    final_confidence: str
    description: str
    agreement: str  # "unanimous", "strong", "moderate", "weak", "conflict"
    voters: list[HybridVoter]
    weighted_scores: dict  # action -> weighted score (0-1)
    dt_probabilities: dict  # action -> DT probability
    conflict: ConflictInfo
    context: Optional[dict] = None


class ChainStep(BaseModel):
    step: int
    action: str
    description: str
    confidence: str
    phase: str


class ChainResponse(BaseModel):
    primary_action: str
    primary_confidence: str
    steps: list[ChainStep]
    total_steps: int
    context: Optional[dict] = None


# ──────────────────────────────────────────────
#  Helper: compute derived context
# ──────────────────────────────────────────────

def _build_context(profile: FinancialProfile) -> dict:
    """Compute derived features, risk score, and segment for display/context."""
    d = profile.model_dump()
    equity = d["current_equity_value"]
    debt = d["current_debt_value"]
    total = equity + debt

    risk = compute_risk_score(**d)
    seg = classify_segment(**d)

    return {
        "portfolio_total": total,
        "equity_pct": round((equity / total * 100), 2) if total > 0 else 0.0,
        "sip_ratio": round(d["sip_amount"] / d["salary"], 4) if d["salary"] > 0 else 0.0,
        "diversification_score": d["num_stocks"] + d["num_mutual_funds"],
        "sip_status": f"Active @ INR {d['sip_amount']:,}/mo" if d["sip_active"] else "Inactive",
        "risk_score": risk["risk_score"],
        "risk_label": risk["risk_label"],
        "segment": seg["segment"],
        "segment_label": seg["profile"]["label"],
    }


# ──────────────────────────────────────────────
#  Helper: ML prediction for single profile
# ──────────────────────────────────────────────

def _ml_predict_single(profile: FinancialProfile) -> dict:
    """Run a single profile through all 3 ML models. Returns predictions dict."""
    preds, _ = _ml_predict_with_proba(profile)
    return preds


def _ml_predict_with_proba(profile: FinancialProfile) -> tuple:
    """
    Run a single profile through all 3 ML models.
    Returns (predictions_dict, dt_proba_dict).
    dt_proba_dict maps class_name -> probability from Decision Tree.
    """
    import pandas as pd
    import numpy as np
    from financial_engine.model_training import pandas_to_orange
    from financial_engine.predictor import compute_derived

    target_enc = _ml_data_bundle["target_enc"]
    encoders = _ml_data_bundle["encoders"]
    feature_names = _ml_data_bundle["feature_names"]
    class_names = list(target_enc.classes_)
    user_input = profile.model_dump()
    extended = compute_derived(user_input)

    results = {}

    # Decision Tree (with probabilities)
    row_encoded = {}
    for feat in feature_names:
        if feat in encoders:
            row_encoded[feat] = encoders[feat].transform([extended[feat]])[0]
        else:
            row_encoded[feat] = extended[feat]
    X_row = pd.DataFrame([row_encoded])[feature_names]
    dt_idx = _ml_models["Decision Tree"].predict(X_row)[0]
    results["Decision Tree"] = class_names[dt_idx]

    # Decision Tree probabilities
    dt_proba_raw = _ml_models["Decision Tree"].predict_proba(X_row)[0]
    dt_proba = {class_names[i]: round(float(p), 4) for i, p in enumerate(dt_proba_raw) if p > 0.01}

    # RIPPER
    X_raw = pd.DataFrame([extended])
    ripper_label = "HOLD"
    for cls in sorted(_ml_models["RIPPER"].keys()):
        pred = _ml_models["RIPPER"][cls].predict(X_raw)
        if pred[0] == 1:
            ripper_label = cls
            break
    results["RIPPER"] = ripper_label

    # CN2
    raw_row = pd.DataFrame([{**extended, "action": "HOLD"}])
    orange_row = pandas_to_orange(raw_row, "action")
    cn2_idx = int(_ml_models["CN2"](orange_row[0]))
    cn2_classes = list(orange_row.domain.class_var.values)
    results["CN2"] = cn2_classes[cn2_idx]

    return results, dt_proba


# ──────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    """Serve the frontend UI."""
    html_file = TEMPLATE_DIR / "index.html"
    return html_file.read_text(encoding="utf-8")


@app.get("/health")
def health_check():
    """Health check."""
    return {
        "status": "healthy",
        "service": "AI Financial Decision Engine v2",
        "ml_models_loaded": _ml_models is not None,
    }


@app.get("/actions")
def list_actions():
    """List all 13 possible financial actions with descriptions."""
    return {
        "count": len(ACTION_DESCRIPTIONS),
        "actions": [
            {"action": k, "description": v}
            for k, v in sorted(ACTION_DESCRIPTIONS.items())
        ],
    }


@app.get("/schema")
def input_schema():
    """Return input feature schema with valid ranges."""
    return {
        "features": [
            {"name": "salary", "type": "int", "min": 20000, "max": 100000, "description": "Monthly salary (INR)"},
            {"name": "monthly_savings", "type": "int", "min": 2000, "max": 50000, "description": "Monthly savings (INR)"},
            {"name": "goal_years", "type": "int", "min": 1, "max": 15, "description": "Years to financial goal"},
            {"name": "risk_level", "type": "string", "values": list(VALID_RISK_LEVELS), "description": "Risk tolerance"},
            {"name": "dependents", "type": "int", "min": 0, "max": 5, "description": "Number of dependents"},
            {"name": "investment_experience", "type": "string", "values": list(VALID_EXPERIENCE), "description": "Investment experience level"},
            {"name": "emergency_fund_months", "type": "int", "min": 0, "max": 12, "description": "Emergency fund (months)"},
            {"name": "debt_to_income", "type": "float", "min": 0, "max": 0.6, "description": "Debt-to-income ratio"},
            {"name": "current_equity_value", "type": "int", "min": 0, "max": 500000, "description": "Current equity holdings (INR)"},
            {"name": "current_debt_value", "type": "int", "min": 0, "max": 500000, "description": "Current debt holdings (INR)"},
            {"name": "sip_amount", "type": "int", "min": 0, "max": 25000, "description": "Monthly SIP amount (INR)"},
            {"name": "sip_active", "type": "boolean", "description": "Is SIP currently active?"},
            {"name": "num_stocks", "type": "int", "min": 0, "max": 20, "description": "Number of stocks held"},
            {"name": "num_mutual_funds", "type": "int", "min": 0, "max": 15, "description": "Number of mutual funds"},
        ],
        "derived_features": [
            {"name": "portfolio_total", "formula": "current_equity_value + current_debt_value"},
            {"name": "equity_pct", "formula": "(current_equity_value / portfolio_total) * 100"},
            {"name": "sip_ratio", "formula": "sip_amount / salary"},
            {"name": "diversification_score", "formula": "num_stocks + num_mutual_funds"},
        ],
    }


@app.post("/risk-score")
def get_risk_score(profile: FinancialProfile):
    """
    Compute a granular risk score (0-100) from 5 financial dimensions:
    income stability, dependency burden, safety net, portfolio volatility, time horizon.
    """
    user = profile.model_dump()
    risk = compute_risk_score(**user)
    return risk


@app.post("/segment")
def get_segment(profile: FinancialProfile):
    """
    Classify the user into a micro-segment persona based on their financial profile.
    Returns segment type, traits, recommended action bias, warnings, and match scores.
    """
    user = profile.model_dump()
    result = classify_segment(**user)
    return result


@app.post("/cash-flow-buffer")
def get_cash_flow_buffer(profile: FinancialProfile):
    """
    Cash Flow Buffer Engine.
    Computes survival months, liquid reserves, emergency burn rate,
    buffer target analysis, and actionable insights.

    survival_months = total_liquid_savings / emergency_monthly_burn
    """
    user = profile.model_dump()
    result = compute_cash_flow_buffer(**user)
    return result


@app.post("/income-shock")
def get_income_shock_simulation(profile: FinancialProfile):
    """
    Income Shock Simulation Engine.
    Simulates 4 extreme scenarios:
      1. Income drops 50% for 6 months
      2. Zero income for 3 months
      3. Zero income for 6 months
      4. Permanent 30% pay cut

    Returns resilience score (0-100), per-scenario survival analysis,
    goal impact, and decision adjustments.
    """
    user = profile.model_dump()
    result = simulate_income_shocks(**user)
    return result


@app.post("/income-shock/with-goals")
def get_income_shock_with_goals(profile: FinancialProfile, goals: list[dict] = None):
    """
    Income Shock Simulation with Goal Impact Analysis.
    Same as /income-shock but also checks if each goal survives the shock.
    """
    user = profile.model_dump()
    result = simulate_income_shocks(**user, goals=goals)
    return result


@app.get("/income-types")
def list_income_types():
    """List all supported income types with stability and volatility metrics."""
    return {
        "count": len(INCOME_TYPES),
        "types": [
            {
                "key": k,
                "label": v["label"],
                "base_stability": v["base_stability"],
                "volatility": v["volatility"],
                "description": v["description"],
            }
            for k, v in INCOME_TYPES.items()
        ],
    }


class GoalInput(BaseModel):
    name: str = Field(..., description="Goal name (e.g., 'Son's College')")
    target: int = Field(..., ge=0, description="Target amount in today's INR")
    saved: int = Field(0, ge=0, description="Amount already saved")
    years: int = Field(..., ge=1, le=30, description="Years to goal")
    priority: str = Field("medium", description="critical / high / medium / low")


@app.post("/inflation/analyze")
def analyze_inflation(goals: list[GoalInput]):
    """
    Full inflation analysis for multiple goals.

    3-Layer system:
      Layer 1: Goal-based inflation mapping (category-specific ranges)
      Layer 2: Scenario simulation (optimistic / expected / worst case)
      Layer 3: Inflation risk score (0-100) with buffer recommendation
      Layer 4: Dynamic recalibration (year-by-year cost growth)

    Returns per-goal scenarios, inflation-adjusted targets, risk scores, and insights.
    """
    goal_dicts = [g.model_dump() for g in goals]
    return analyze_goal_inflation(goal_dicts)


@app.post("/inflation/scenario")
def inflation_scenario(goal_name: str, today_cost: int, years: int, goal_type: str = None):
    """
    Simulate 3 inflation scenarios for a single goal.

    Returns optimistic, expected, and worst-case future costs.
    """
    return simulate_inflation_scenarios(goal_name, today_cost, years, goal_type)


@app.post("/inflation/risk-score")
def inflation_risk_score(goal_type: str, years: int):
    """
    Compute inflation risk score (0-100) for a goal type + time horizon.

    Returns score, label, component breakdown, and recommended buffer %.
    """
    return compute_inflation_risk_score(goal_type, years)


@app.get("/inflation/categories")
def list_inflation_categories():
    """List all goal categories with their inflation ranges."""
    return {
        "count": len(GOAL_INFLATION_MAP),
        "categories": [
            {
                "goal_type": k,
                "low_inflation": f"{v[0]:.0%}",
                "high_inflation": f"{v[1]:.0%}",
                "expected": f"{(v[0] + v[1]) / 2:.0%}",
            }
            for k, v in GOAL_INFLATION_MAP.items()
        ],
    }


@app.post("/market/simulate")
def simulate_market_risk(goals: list[GoalInput], monthly_savings: int = 20000,
                          risk_level: str = "medium", num_simulations: int = 500):
    """
    Full market risk analysis with Monte Carlo simulation.

    Runs 500 simulated futures per goal to compute:
      - Success probability (% of simulations that meet target)
      - Worst/expected/best case outcomes (percentiles)
      - Sequence risk (crash early vs crash late impact)
      - Timing risk (short horizon + equity = danger)
      - Market risk score (0-100)
      - Decision adjustments

    This is the REAL answer to "will my goal succeed?" — not a single return assumption.
    """
    goal_dicts = [g.model_dump() for g in goals]
    return analyze_market_risk(goal_dicts, monthly_savings, risk_level,
                                min(num_simulations, 1000))


@app.post("/market/monte-carlo")
def monte_carlo_single(strategy: str, years: int, monthly_sip: int,
                        initial_savings: int = 0, target: int = 1000000,
                        num_simulations: int = 500):
    """
    Run Monte Carlo simulation for a single goal/strategy.

    Returns success probability, percentile outcomes, and regime distribution.
    """
    valid_strategies = {"Liquid", "Debt", "Hybrid", "Equity", "Aggressive"}
    if strategy not in valid_strategies:
        raise HTTPException(400, f"Strategy must be one of {valid_strategies}")
    return run_monte_carlo(strategy, years, monthly_sip, initial_savings,
                            target, min(num_simulations, 1000))


@app.post("/market/sequence-risk")
def sequence_risk(strategy: str, years: int, monthly_sip: int,
                   initial_savings: int = 0):
    """
    Analyze sequence risk: crash early vs crash late.

    Same average return, different outcome. This shows WHY sequence matters.
    """
    valid_strategies = {"Liquid", "Debt", "Hybrid", "Equity", "Aggressive"}
    if strategy not in valid_strategies:
        raise HTTPException(400, f"Strategy must be one of {valid_strategies}")
    return analyze_sequence_risk(strategy, years, monthly_sip, initial_savings)


@app.post("/market/timing-risk")
def timing_risk(strategy: str, years: int):
    """
    Assess timing risk for a strategy + horizon combination.

    Short horizon + equity = high timing risk.
    """
    valid_strategies = {"Liquid", "Debt", "Hybrid", "Equity", "Aggressive"}
    if strategy not in valid_strategies:
        raise HTTPException(400, f"Strategy must be one of {valid_strategies}")
    return assess_timing_risk(strategy, years)


@app.get("/market/regimes")
def list_market_regimes():
    """List all market regimes with probabilities and return profiles."""
    return {
        "count": len(MARKET_REGIMES),
        "regimes": [
            {
                "regime": k,
                "label": v["label"],
                "probability": f"{v['probability']:.0%}",
                "returns": {s: f"{r:.0%}" for s, r in v["returns"].items()},
            }
            for k, v in MARKET_REGIMES.items()
        ],
    }


class TaxProfileRequest(BaseModel):
    annual_income: int = Field(..., ge=0, description="Gross annual income (INR)")
    income_type: str = Field("salaried", description="salaried / freelance / business / pension")
    regime: str = Field("new", description="Tax regime: new / old")
    deductions_80c: int = Field(0, ge=0, le=150000, description="80C deductions excl ELSS")
    deductions_80d: int = Field(0, ge=0, le=100000, description="80D health insurance")
    hra_claimed: int = Field(0, ge=0, description="HRA exemption (old regime)")
    existing_elss: int = Field(0, ge=0, description="ELSS already invested this FY")


@app.post("/tax/profile")
def get_tax_profile(req: TaxProfileRequest):
    """
    Compute user's tax profile: slab, effective rate, total tax, remaining deductions.
    """
    return compute_user_tax_profile(
        req.annual_income, req.income_type, req.regime,
        req.deductions_80c, req.deductions_80d, req.hra_claimed, req.existing_elss,
    )


@app.post("/tax/analyze")
def tax_analysis(salary: int, goals: list[GoalInput], risk_level: str = "medium",
                  income_type: str = "salaried", regime: str = "new",
                  deductions_80c: int = 0, deductions_80d: int = 0,
                  hra_claimed: int = 0, existing_elss: int = 0):
    """
    Full tax analysis across all goals.

    7-Layer engine:
      1. Config-driven tax rules (versioned, policy-aware)
      2. User tax profile (slab, effective rate)
      3. After-tax returns per strategy
      4. Tax-aware decisions (ELSS, holding period, regime)
      5. Policy version tracking
      6. Tax impact simulation (pre vs post-tax corpus)
      7. Tax optimization strategies

    Shows how tax reduces actual returns and what to do about it.
    """
    goal_dicts = [g.model_dump() for g in goals]
    return analyze_tax_impact(
        salary, goal_dicts, risk_level, income_type, regime,
        deductions_80c, deductions_80d, hra_claimed, existing_elss,
    )


@app.post("/tax/after-tax-return")
def after_tax_return(strategy: str, pre_tax_return: float, holding_years: int,
                      marginal_rate: float = 0.30):
    """
    Compute after-tax return for a strategy.

    Shows: pre-tax return -> tax rate -> after-tax return -> tax drag.
    """
    return compute_after_tax_return(strategy, pre_tax_return, holding_years, marginal_rate)


@app.post("/tax/optimize")
def tax_optimize(req: TaxProfileRequest, goals: list[GoalInput],
                  risk_level: str = "medium"):
    """
    Generate tax optimization strategies for the user.

    Returns actionable suggestions: ELSS, holding period, LTCG harvesting,
    growth vs dividend, NPS, regime comparison.
    """
    from financial_engine.goal_planner import _get_strategy
    tax_profile = compute_user_tax_profile(
        req.annual_income, req.income_type, req.regime,
        req.deductions_80c, req.deductions_80d, req.hra_claimed, req.existing_elss,
    )
    goal_strategies = [
        {"name": g.name, "strategy": _get_strategy(g.years, risk_level), "years": g.years}
        for g in goals
    ]
    return generate_tax_optimizations(tax_profile, goal_strategies)


@app.get("/tax/rules")
def get_tax_rules():
    """Get current active tax rules (FY 2025-26 by default)."""
    return get_current_rules()


@app.get("/tax/versions")
def get_tax_versions():
    """List all available tax rule versions (for policy change tracking)."""
    return list_available_versions()


@app.get("/segments")
def list_segments():
    """List all available micro-segments with descriptions."""
    return {
        "count": len(SEGMENT_PROFILES),
        "segments": [
            {"key": k, "label": v["label"], "description": v["description"]}
            for k, v in SEGMENT_PROFILES.items()
        ],
    }


@app.post("/recommend")
def get_fund_recommendation(profile: FinancialProfile):
    """
    Deterministic Recommendation Engine.
    No LLM. No API cost. No hallucination. Pure logic.

    Maps: ML Action + Risk + Goal → Investment Category + Fund Types + Allocation
    """
    user = profile.model_dump()
    action, confidence = rule_predict(**user)
    intent = compute_intensity(action, **user)
    rec = get_recommendation(action, user["risk_level"], user["goal_years"])

    return {
        "action": action,
        "action_detail": intent["action_detail"],
        "confidence": f"{confidence}%",
        "recommendation": rec,
    }


@app.post("/analyze")
def analyze_holdings(profile: DetailedProfile):
    """
    Portfolio analysis from itemized holdings.
    Detects sector concentration, gaps, duplicates, and computes derived features.
    """
    stocks = [s.model_dump() for s in profile.stocks]
    mfs = [f.model_dump() for f in profile.mutual_funds]
    debts = [d.model_dump() for d in profile.debt_investments]
    analysis = analyze_portfolio(stocks, mfs, debts)
    return analysis


@app.post("/predict/smart")
def predict_smart(profile: DetailedProfile):
    """
    SMART PREDICTION — accepts itemized holdings (stocks, mutual funds, debt).

    Analyzes portfolio for sector concentration, gaps, and duplicates,
    then generates action + intensity + opportunity cost + recommendation
    that is AWARE of what you already own.
    """
    stocks = [s.model_dump() for s in profile.stocks]
    mfs = [f.model_dump() for f in profile.mutual_funds]
    debts = [d.model_dump() for d in profile.debt_investments]

    # 1. Analyze itemized holdings
    analysis = analyze_portfolio(stocks, mfs, debts)
    flat = profile.to_flat_profile(analysis)

    # 2. Action + confidence
    action, confidence = rule_predict(**flat)
    intent = compute_intensity(action, **flat)

    # 3. Opportunity cost
    opp = compute_opportunity_cost(action, flat, intent["metrics"])

    # 4. Risk score + segment
    risk = compute_risk_score(**flat)
    seg = classify_segment(**flat)

    # 5. Recommendation (holdings-aware)
    rec = get_recommendation(action, flat["risk_level"], flat["goal_years"])

    # Filter out funds user already owns
    owned_names = {f["name"] for f in mfs} | {d["name"] for d in debts}
    owned_cats = set(analysis["owned_mf_categories"])
    for ft in rec.get("fund_types", []):
        ft["already_owned"] = any(ex in owned_names for ex in ft.get("examples", []))
        ft["category_owned"] = ft.get("type", "") in [
            MF_CATEGORIES.get(n, {}).get("category", "") for n in owned_names
        ] if False else ft.get("type", "").replace(" Fund", "") in owned_cats

    # 6. Smart suggestions based on gaps
    smart_suggestions = []
    if analysis["concentration"]:
        top = analysis["concentration"][0]
        pct = top.get("percentage", "")
        pct_str = f" ({pct}%)" if pct else ""
        smart_suggestions.append(f"Reduce {top['sector']} exposure{pct_str} — add other sectors")

    for gap in analysis["gaps"].get("missing_fund_categories", [])[:2]:
        smart_suggestions.append(gap["reason"])

    if analysis["gaps"]["missing_sectors"]:
        missing = ", ".join(list(analysis["gaps"]["missing_sectors"])[:3])
        smart_suggestions.append(f"No exposure to {missing} — consider adding for diversification")

    if analysis["duplicates"]:
        for d in analysis["duplicates"][:2]:
            smart_suggestions.append(d)

    return {
        "action": action,
        "action_detail": intent["action_detail"],
        "confidence": f"{confidence}%",
        "intensity": intent["metrics"],
        "opportunity_cost": {
            "cost_of_inaction": opp["cost_of_inaction"],
            "nudge": opp["nudge"],
        },
        "recommendation": rec,
        "portfolio_analysis": {
            "holdings": analysis["holdings_summary"],
            "sector_exposure": analysis["sector_exposure"],
            "concentration_warnings": analysis["concentration"],
            "gaps": analysis["gaps"],
            "duplicates": analysis["duplicates"],
        },
        "smart_suggestions": smart_suggestions,
        "context": {
            "portfolio_total": analysis["derived"]["portfolio_total"],
            "equity_pct": analysis["derived"]["equity_pct"],
            "num_stocks": analysis["derived"]["num_stocks"],
            "num_mutual_funds": analysis["derived"]["num_mutual_funds"],
            "risk_score": risk["risk_score"],
            "risk_label": risk["risk_label"],
            "segment": seg["segment"],
            "segment_label": seg["profile"]["label"],
        },
    }


@app.get("/models/status")
def models_status():
    """Check status of loaded ML models."""
    if _ml_models is None:
        return {
            "rule_engine": "ready",
            "decision_tree": "not loaded",
            "ripper": "not loaded",
            "cn2": "not loaded",
            "message": "Run `python main.py train` first to enable ML endpoints.",
        }
    return {
        "rule_engine": "ready",
        "decision_tree": "ready",
        "ripper": f"ready ({len(_ml_models['RIPPER'])} class models)",
        "cn2": "ready",
    }


@app.post("/predict", response_model=PredictionResponse)
def predict_rule_engine(profile: FinancialProfile):
    """
    Fast prediction using the pure if-else rule engine.
    No ML dependencies, instant response. Context-aware.
    Includes action intensity with specific amounts.
    """
    user = profile.model_dump()
    action, confidence = rule_predict(**user)
    ctx = _build_context(profile)
    intent = compute_intensity(action, **user)
    opp = compute_opportunity_cost(action, user, intent["metrics"])
    return PredictionResponse(
        action=action,
        action_detail=intent["action_detail"],
        description=ACTION_DESCRIPTIONS[action],
        model="rule_engine",
        confidence=f"{confidence}%",
        intensity=intent["metrics"],
        opportunity_cost=opp,
        context=ctx,
    )


@app.post("/predict/full")
def predict_full(profile: FinancialProfile):
    """
    ULTIMATE ENDPOINT — The complete financial advisor pipeline:

    ML Engine → WHAT to do (action + intensity + confidence)
    Risk Score → HOW risky you are (0-100)
    Segment → WHO you are (investor persona)
    Opportunity Cost → WHY you should act (behavioral nudge)
    Product Engine → WHERE to invest (real-time fund data)
    Recommendation Engine → Fund types + allocation (deterministic)
    """
    user = profile.model_dump()
    ctx = _build_context(profile)

    # 1. Action + Confidence + Intensity
    action, confidence = rule_predict(**user)
    intent = compute_intensity(action, **user)

    # 2. Opportunity Cost
    opp = compute_opportunity_cost(action, user, intent["metrics"])

    # 3. Deterministic recommendation
    rec = get_recommendation(action, user["risk_level"], user["goal_years"])

    # 4. Fetch real-time market data
    products = fetch_products_for_action(action)

    return {
        "action": action,
        "action_detail": intent["action_detail"],
        "description": ACTION_DESCRIPTIONS[action],
        "confidence": f"{confidence}%",
        "intensity": intent["metrics"],
        "opportunity_cost": {
            "cost_of_inaction": opp["cost_of_inaction"],
            "nudge": opp["nudge"],
            "numbers": opp["numbers"],
        },
        "recommendation": rec,
        "market_data": [
            {k: v for k, v in p.items() if k != "symbol"}
            for p in products if p.get("data_available")
        ],
        "context": ctx,
    }


@app.post("/predict/chain", response_model=ChainResponse)
def predict_chained(profile: FinancialProfile):
    """
    Multi-step chained decision engine.
    Evaluates ALL applicable rules and returns a prioritized action plan
    with phases (immediate -> short_term -> long_term).
    """
    user = profile.model_dump()
    chain = rule_predict_chain(**user)
    ctx = _build_context(profile)

    steps = [
        ChainStep(
            step=s["step"],
            action=s["action"],
            description=s["description"],
            confidence=f"{s['confidence']}%",
            phase=s["phase"],
        )
        for s in chain
    ]

    return ChainResponse(
        primary_action=chain[0]["action"],
        primary_confidence=f"{chain[0]['confidence']}%",
        steps=steps,
        total_steps=len(steps),
        context=ctx,
    )


# ──────────────────────────────────────────────
#  Ensemble Weights & Conflict Resolution
# ──────────────────────────────────────────────

# Model weights (must sum to 1.0)
MODEL_WEIGHTS = {
    "Decision Tree": 0.40,   # highest — best accuracy, gives probabilities
    "Rule Engine":   0.30,   # domain expert, explainable
    "RIPPER":        0.20,   # rule learner, good generalization
    "CN2":           0.10,   # weakest but adds diversity
}

# Safety-critical actions where rule engine gets veto power
SAFETY_ACTIONS = {"EMERGENCY_FUND_BUILD", "STOP_SIP", "SELL", "REBALANCE"}


@app.post("/predict/hybrid", response_model=HybridResponse)
def predict_hybrid(profile: FinancialProfile):
    """
    ENSEMBLE INTELLIGENCE: Weighted confidence-based voting.

    Decision Tree (0.40) + Rule Engine (0.30) + RIPPER (0.20) + CN2 (0.10)

    Each model's vote = weight × model_confidence.
    Includes conflict detection, safety-action veto, and DT probability distribution.
    """
    if _ml_models is None:
        raise HTTPException(
            status_code=503,
            detail="ML models not loaded. Run `python main.py train` first.",
        )

    user = profile.model_dump()
    ctx = _build_context(profile)

    # ── 1. Collect predictions + per-model confidence ──
    rule_action, rule_conf = rule_predict(**user)
    ml_preds, dt_proba = _ml_predict_with_proba(profile)

    dt_action = ml_preds["Decision Tree"]
    rip_action = ml_preds["RIPPER"]
    cn2_action = ml_preds["CN2"]

    # Per-model confidence (0-1 scale)
    dt_conf = dt_proba.get(dt_action, 0.5)                   # from predict_proba
    rule_conf_norm = rule_conf / 100                          # rule engine 0-97 -> 0-0.97
    rip_conf = 0.70                                           # RIPPER: no native proba, use 0.70
    cn2_conf = 0.60                                           # CN2: no native proba, use 0.60

    models = {
        "Decision Tree": {"action": dt_action,   "weight": MODEL_WEIGHTS["Decision Tree"],  "conf": dt_conf},
        "Rule Engine":   {"action": rule_action,  "weight": MODEL_WEIGHTS["Rule Engine"],    "conf": rule_conf_norm},
        "RIPPER":        {"action": rip_action,   "weight": MODEL_WEIGHTS["RIPPER"],         "conf": rip_conf},
        "CN2":           {"action": cn2_action,   "weight": MODEL_WEIGHTS["CN2"],            "conf": cn2_conf},
    }

    # ── 2. Weighted Confidence Voting ──
    # Each model contributes: weight × confidence to its chosen action
    score_board = {}
    for name, m in models.items():
        contribution = round(m["weight"] * m["conf"], 4)
        score_board[m["action"]] = round(score_board.get(m["action"], 0) + contribution, 4)

    # Sort descending
    sorted_scores = dict(sorted(score_board.items(), key=lambda x: x[1], reverse=True))
    winner = max(score_board, key=score_board.get)
    winner_score = score_board[winner]

    # ── 3. Conflict Detection ──
    all_actions = [rule_action, dt_action, rip_action, cn2_action]
    unique = set(all_actions)
    ml_actions = {dt_action, rip_action, cn2_action}
    rule_matches_ml = sum(1 for a in [dt_action, rip_action, cn2_action] if a == rule_action)

    if len(unique) == 1:
        conflict_type = "none"
    elif rule_action not in ml_actions:
        conflict_type = "rule_vs_ml"
    else:
        conflict_type = "ml_internal"

    # ── 4. Safety Veto ──
    # If rule engine chose a safety-critical action but ML outvoted it,
    # the rule engine gets override power (domain expert safety guarantee)
    rule_overridden = (winner != rule_action)
    safety_veto = False

    if rule_overridden and rule_action in SAFETY_ACTIONS and rule_conf_norm >= 0.75:
        # Rule engine vetoes — safety takes priority
        winner = rule_action
        winner_score = score_board.get(rule_action, rule_conf_norm * MODEL_WEIGHTS["Rule Engine"])
        safety_veto = True

    # ── 5. Agreement Level ──
    if len(unique) == 1:
        agreement = "unanimous"
    elif rule_matches_ml >= 2 and winner == rule_action:
        agreement = "strong"
    elif winner_score >= 0.50:
        agreement = "moderate"
    elif winner_score >= 0.30:
        agreement = "weak"
    else:
        agreement = "conflict"

    # ── 6. Final Confidence ──
    # Normalize winner_score against theoretical max (1.0 if all models agree at 100%)
    # Then blend with DT probability for the winner
    dt_prob_for_winner = dt_proba.get(winner, 0)
    raw_confidence = (winner_score * 0.6 + dt_prob_for_winner * 0.25 + rule_conf_norm * 0.15) * 100

    # Penalty for disagreement
    if agreement == "conflict":
        raw_confidence *= 0.7
    elif agreement == "weak":
        raw_confidence *= 0.85

    # Bonus for safety veto (we're more confident in safety overrides)
    if safety_veto:
        raw_confidence = max(raw_confidence, rule_conf * 0.9)

    final_confidence = min(int(raw_confidence), 97)

    # ── 7. Build voter details ──
    voters = []
    for name in ["Decision Tree", "Rule Engine", "RIPPER", "CN2"]:
        m = models[name]
        contribution = round(m["weight"] * m["conf"], 4)
        voters.append(HybridVoter(
            model=name,
            action=m["action"],
            weight=m["weight"],
            model_confidence=f"{int(m['conf'] * 100)}%",
            weighted_contribution=f"{contribution:.4f}",
        ))

    conflict_info = ConflictInfo(
        has_conflict=conflict_type != "none",
        conflict_type=conflict_type,
        rule_engine_overridden=rule_overridden and not safety_veto,
        resolution_method="safety_veto" if safety_veto else "weighted_confidence_vote",
    )

    # ── 8. LLM Explanation ──
    return HybridResponse(
        final_action=winner,
        final_confidence=f"{final_confidence}%",
        description=ACTION_DESCRIPTIONS[winner],
        agreement=agreement,
        voters=voters,
        weighted_scores=sorted_scores,
        dt_probabilities=dt_proba,
        conflict=conflict_info,
        context=ctx,
    )


@app.post("/predict/ml", response_model=MLPredictionResponse)
def predict_ml(profile: FinancialProfile):
    """
    Prediction from all 3 ML models (Decision Tree, RIPPER, CN2)
    with majority-vote consensus. Context-aware.
    """
    if _ml_models is None:
        raise HTTPException(
            status_code=503,
            detail="ML models not loaded. Run `python main.py train` first.",
        )

    preds = _ml_predict_single(profile)
    ctx = _build_context(profile)

    # Build per-model responses
    dt_action = preds["Decision Tree"]
    rip_action = preds["RIPPER"]
    cn2_action = preds["CN2"]

    # Consensus
    votes = [dt_action, rip_action, cn2_action]
    counts = Counter(votes)
    majority, count = counts.most_common(1)[0]

    if count == 3:
        consensus_label = "unanimous"
    elif count == 2:
        consensus_label = "majority (2/3)"
    else:
        consensus_label = "no consensus"

    return MLPredictionResponse(
        decision_tree={"action": dt_action, "description": ACTION_DESCRIPTIONS[dt_action]},
        ripper={"action": rip_action, "description": ACTION_DESCRIPTIONS[rip_action]},
        cn2={"action": cn2_action, "description": ACTION_DESCRIPTIONS[cn2_action]},
        consensus={
            "action": majority,
            "description": ACTION_DESCRIPTIONS[majority],
            "agreement": consensus_label,
            "votes": dict(counts),
            "context": ctx,
        },
    )


@app.post("/predict/batch", response_model=BatchResponse)
def predict_batch(batch: BatchRequest):
    """
    Batch predictions using the rule engine.
    Up to 100 profiles per request.
    """
    results = []
    for profile in batch.profiles:
        user = profile.model_dump()
        action, confidence = rule_predict(**user)
        ctx = _build_context(profile)
        results.append(PredictionResponse(
            action=action,
            description=ACTION_DESCRIPTIONS[action],
            model="rule_engine",
            confidence=f"{confidence}%",
            context=ctx,
        ))
    return BatchResponse(results=results, count=len(results))


# ══════════════════════════════════════════════════════════════════════════════
#  REAL-TIME STOCK DATA & ANALYSIS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Pydantic models for new endpoints ─────────────────────────────────────────

class HoldingItem(BaseModel):
    ticker: str
    quantity: float = Field(..., ge=0)
    current_price: float = Field(..., ge=0)
    category: Optional[str] = None
    asset_type: Optional[str] = None
    holding_period: Optional[str] = None  # "LTCG" | "STCG" | "unknown"


class RebalanceRequest(BaseModel):
    holdings: list[HoldingItem]
    risk_level: str = "medium"
    target_allocation: Optional[dict] = None
    rebalance_threshold: float = 5.0
    min_trade_value: float = 1000.0
    existing_fund_names: list[str] = Field(
        default_factory=list,
        description="Mutual fund names already held. BUY suggestions will exclude these "
                    "to prevent 'buy what you already own' conflicts."
    )


class AlertCreateRequest(BaseModel):
    alert_type: str
    ticker: Optional[str] = None
    target_value: Optional[float] = None
    message: str = ""
    direction: str = "above"
    notify_email: Optional[str] = None


class WatchdogStartRequest(BaseModel):
    tickers: list[str]
    check_interval_prices: int = 300
    check_interval_technicals: int = 900
    check_interval_portfolio: int = 3600
    check_interval_news: int = 1800


# ── Stock data ─────────────────────────────────────────────────────────────────

@app.get("/stocks/{ticker}", tags=["Real-Time Data"],
         summary="Current price and fundamentals for a stock")
def get_stock_data(ticker: str):
    """Returns current price, change %, volume, and key fundamentals (PE, EPS, D/E, ROE…)."""
    from financial_engine.stock_data_fetcher import get_stock_price, get_fundamentals
    return {
        "price":        get_stock_price(ticker),
        "fundamentals": get_fundamentals(ticker),
    }


@app.get("/stocks/{ticker}/history", tags=["Real-Time Data"],
         summary="OHLCV historical data")
def get_stock_history(ticker: str, period: str = "6mo", interval: str = "1d"):
    """
    Historical OHLCV data.
    period:   1d | 5d | 1mo | 3mo | 6mo | 1y | 2y | 5y
    interval: 1m | 5m | 15m | 1h  | 1d  | 1wk | 1mo
    """
    from financial_engine.stock_data_fetcher import get_historical_data
    df = get_historical_data(ticker, period=period, interval=interval)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")
    records = df.reset_index().rename(columns={"index": "date"})
    records["date"] = records["date"].astype(str)
    return {"ticker": ticker, "period": period, "interval": interval,
            "rows": len(records), "data": records.to_dict(orient="records")}


# ── Technical indicators & signals ────────────────────────────────────────────

@app.get("/stocks/{ticker}/indicators", tags=["Technical Analysis"],
         summary="All technical indicators for a ticker")
def get_indicators(ticker: str, period: str = "6mo"):
    """Returns RSI, MACD, Bollinger Bands, Stochastic, ADX, ATR, volume ratio, and MAs."""
    from financial_engine.stock_data_fetcher import get_historical_data
    from financial_engine.technical_indicators import get_all_indicators
    df = get_historical_data(ticker, period=period)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")
    ind = get_all_indicators(df)
    if not ind:
        raise HTTPException(status_code=422, detail="Insufficient data to compute indicators (need ≥30 bars)")
    return {"ticker": ticker, "period": period, "indicators": ind}


@app.get("/stocks/{ticker}/signals", tags=["Technical Analysis"],
         summary="Buy / Sell / Hold signal with strength")
def get_signals(ticker: str, period: str = "6mo"):
    """
    Weighted signal combining RSI (20%), MACD (25%), MA trend (20%),
    Bollinger Bands (15%), Stochastic (10%), Volume (10%).

    score: -1.0 (strong sell) → +1.0 (strong buy)
    """
    from financial_engine.signal_engine import generate_signals
    return generate_signals(ticker, period=period)


# ── Stock scoring & ranking ───────────────────────────────────────────────────

@app.get("/stocks/{ticker}/score", tags=["Stock Scoring"],
         summary="Composite 0-100 score: Fundamental + Technical + Valuation + Sentiment")
def get_stock_score(ticker: str):
    """
    Score breakdown:
      Fundamental  30% — PE, EPS growth, debt, ROE, margins
      Technical    40% — RSI/MACD/MA momentum
      Valuation    20% — analyst target, 52w position, PEG
      Sentiment    10% — news keyword sentiment
    """
    from financial_engine.stock_scorer import score_stock
    return score_stock(ticker)


class RankRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1, max_length=50)
    owned_tickers: list[str] = Field(
        default_factory=list,
        description="Tickers already held in portfolio. BUY signals become ADD_MORE for these."
    )


@app.post("/stocks/rank", tags=["Stock Scoring"],
          summary="Rank a list of stocks by composite score")
def rank_stocks_endpoint(req: RankRequest):
    """
    POST body: {"tickers": ["RELIANCE.NS", "TCS.NS"], "owned_tickers": ["RELIANCE.NS"]}
    Returns stocks sorted by score (highest first) with rank numbers.
    Stocks in owned_tickers get ADD_MORE instead of BUY to avoid duplicate purchase advice.
    """
    from financial_engine.stock_scorer import rank_stocks
    return {"ranked": rank_stocks(req.tickers, owned_tickers=req.owned_tickers),
            "count": len(req.tickers)}


# ── Sentiment analysis ────────────────────────────────────────────────────────

@app.get("/stocks/{ticker}/sentiment", tags=["Sentiment"],
         summary="News sentiment for one stock")
def get_ticker_sentiment(ticker: str):
    """Keyword-based sentiment from recent news. Score: -1 (bearish) to +1 (bullish)."""
    from financial_engine.sentiment_analyzer import get_stock_sentiment
    return get_stock_sentiment(ticker)


@app.post("/market/sentiment", tags=["Sentiment"],
          summary="Aggregate sentiment across a basket of tickers")
def get_market_sentiment_endpoint(tickers: list[str]):
    """Returns per-ticker sentiments and an overall market mood score."""
    if not tickers:
        raise HTTPException(status_code=400, detail="Provide at least one ticker")
    from financial_engine.sentiment_analyzer import get_market_sentiment
    return get_market_sentiment(tickers)


# ── Portfolio rebalancing ─────────────────────────────────────────────────────

@app.post("/portfolio/rebalance", tags=["Portfolio"],
          summary="Generate specific buy/sell rebalancing instructions")
def portfolio_rebalance(req: RebalanceRequest):
    """
    Input: list of holdings with ticker, quantity, current_price.
    Output: drift analysis, sell orders (with quantities), buy orders (with INR amounts
    and suggested instruments), tax-efficient execution order.
    """
    from financial_engine.rebalancing_engine import generate_rebalancing_plan
    holdings = [h.model_dump() for h in req.holdings]
    return generate_rebalancing_plan(
        holdings,
        risk_level=req.risk_level,
        target_allocation=req.target_allocation,
        rebalance_threshold=req.rebalance_threshold,
        min_trade_value=req.min_trade_value,
        existing_fund_names=req.existing_fund_names,
    )


# ── Alerts ────────────────────────────────────────────────────────────────────

@app.get("/alerts", tags=["Alerts"],
         summary="List all active alerts")
def list_alerts_endpoint(include_inactive: bool = False):
    """Returns all saved alerts. Use include_inactive=true to see triggered/inactive ones."""
    from financial_engine.alert_manager import list_alerts
    return {"alerts": list_alerts(active_only=not include_inactive)}


@app.post("/alerts", tags=["Alerts"],
          summary="Create a new price / RSI / portfolio alert")
def create_alert_endpoint(req: AlertCreateRequest):
    """
    alert_type options:
      price_target | stop_loss | rsi_overbought | rsi_oversold |
      rebalance_needed | news_alert | custom
    """
    from financial_engine.alert_manager import create_alert
    try:
        alert = create_alert(
            req.alert_type,
            ticker=req.ticker,
            target_value=req.target_value,
            message=req.message,
            direction=req.direction,
            notify_email=req.notify_email,
        )
        return {"status": "created", "alert": alert}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/alerts/{alert_id}", tags=["Alerts"],
            summary="Delete an alert by ID")
def delete_alert_endpoint(alert_id: str):
    from financial_engine.alert_manager import delete_alert
    if delete_alert(alert_id):
        return {"status": "deleted", "id": alert_id}
    raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")


@app.post("/alerts/check", tags=["Alerts"],
          summary="Manually trigger alert evaluation for a list of tickers")
def check_alerts_endpoint(tickers: list[str]):
    """Runs price + RSI checks immediately and returns any triggered alerts."""
    from financial_engine.alert_manager import check_all_alerts
    triggered = check_all_alerts(tickers)
    return {"triggered": triggered, "count": len(triggered)}


# ── Watchdog ──────────────────────────────────────────────────────────────────

@app.post("/watchdog/start", tags=["Watchdog"],
          summary="Start the 24/7 portfolio monitoring watchdog")
def start_watchdog_endpoint(req: WatchdogStartRequest):
    """
    Launches background threads that continuously check:
    prices (5 min), technicals (15 min), portfolio drift (60 min), news (30 min).
    """
    from financial_engine.watchdog import start_watchdog
    start_watchdog(
        tickers=req.tickers,
        check_interval_prices=req.check_interval_prices,
        check_interval_technicals=req.check_interval_technicals,
        check_interval_portfolio=req.check_interval_portfolio,
        check_interval_news=req.check_interval_news,
    )
    return {"status": "started", "tickers": req.tickers}


@app.post("/watchdog/stop", tags=["Watchdog"],
          summary="Stop the portfolio monitoring watchdog")
def stop_watchdog_endpoint():
    from financial_engine.watchdog import stop_watchdog
    stop_watchdog()
    return {"status": "stopped"}


@app.get("/watchdog/status", tags=["Watchdog"],
         summary="Get current watchdog status")
def watchdog_status_endpoint():
    from financial_engine.watchdog import get_watchdog_status
    return get_watchdog_status()


# ══════════════════════════════════════════════════════════════════════════════
#  SIP CALCULATOR & FUND ADVISORY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class SipProjectRequest(BaseModel):
    monthly_sip: float = Field(..., gt=0, description="Monthly SIP amount in INR")
    years: int         = Field(..., ge=1, le=40)
    cagr: Optional[float]  = Field(None, description="Annual return % (auto if None)")
    risk_level: str        = Field("medium", description="low / medium / high")
    step_up_pct: float     = Field(0.0, ge=0, le=50, description="Annual SIP step-up %")
    existing_corpus: float = Field(0.0, ge=0)


class SipGoalRequest(BaseModel):
    target_amount: float   = Field(..., gt=0)
    years: Optional[int]   = Field(None, ge=1, le=40, description="Horizon for SIP-needed calc")
    monthly_sip: Optional[float] = Field(None, gt=0, description="SIP for duration calc")
    cagr: float            = Field(12.0, description="Annual return %")
    risk_level: str        = Field("medium")
    existing_corpus: float = Field(0.0, ge=0)


class SipSplitRequest(BaseModel):
    monthly_sip: float  = Field(..., gt=0)
    risk_level: str     = Field("medium")
    goal_type: str      = Field("wealth")
    horizon_years: int  = Field(10, ge=1, le=40)
    prefer_low_cost: bool = Field(False)
    existing_sip_funds: list[str] = Field(
        default_factory=list,
        description="Fund names where user already has active SIPs. "
                    "Allocator will skip these and pick the next-best fund per category."
    )


class SipPlanRequest(BaseModel):
    monthly_sip: float      = Field(..., gt=0)
    goal_type: str          = Field("wealth")
    goal_amount: Optional[float] = None
    horizon_years: int      = Field(10, ge=1, le=40)
    risk_level: str         = Field("medium")
    step_up_pct: float      = Field(10.0, ge=0, le=50)
    existing_corpus: float  = Field(0.0, ge=0)
    prefer_low_cost: bool   = Field(False)
    existing_sip_funds: list[str] = Field(
        default_factory=list,
        description="Fund names where user already has active SIPs. "
                    "Allocator will skip these and pick the next-best fund per category."
    )


class FundCompareRequest(BaseModel):
    fund_queries: list[str] = Field(..., min_length=2,
                                    description="Fund names or IDs to compare (min 2)")
    monthly_sip: float      = Field(..., gt=0)
    years: int              = Field(..., ge=1, le=40)
    goal_amount: Optional[float] = None
    existing_corpus: float  = Field(0.0, ge=0)
    step_up_pct: float      = Field(0.0, ge=0, le=50)


# ── Corpus projection ─────────────────────────────────────────────────────────

@app.post("/sip/project", tags=["SIP Calculator"],
          summary="Project corpus: INR X/mo for Y years at Z% CAGR = INR W")
def sip_project(req: SipProjectRequest):
    """
    Returns flat SIP projection, step-up projection (if step_up_pct > 0),
    and year-by-year growth table.
    """
    from financial_engine.sip_calculator import project_corpus, compare_flat_vs_stepup
    flat = project_corpus(req.monthly_sip, req.years, cagr=req.cagr,
                          risk_level=req.risk_level, step_up_pct=0.0,
                          existing_corpus=req.existing_corpus)
    result = {"flat": flat}
    if req.step_up_pct > 0:
        result["step_up"] = compare_flat_vs_stepup(
            req.monthly_sip, req.years,
            cagr=req.cagr or flat["cagr_pct"],
            step_up_pct=req.step_up_pct,
        )
    return result


# ── Goal calculators ──────────────────────────────────────────────────────────

@app.post("/sip/needed", tags=["SIP Calculator"],
          summary="Monthly SIP needed to reach a target corpus in N years")
def sip_needed(req: SipGoalRequest):
    """
    Given a target amount and horizon, returns the exact monthly SIP required.
    Accounts for existing corpus already invested.
    """
    from financial_engine.sip_calculator import sip_needed_for_goal
    if not req.years:
        raise HTTPException(status_code=400, detail="'years' is required for this calculation")
    return sip_needed_for_goal(req.target_amount, req.years, cagr=req.cagr,
                               risk_level=req.risk_level,
                               existing_corpus=req.existing_corpus)


@app.post("/sip/duration", tags=["SIP Calculator"],
          summary="How many months/years to reach a goal at a given SIP amount")
def sip_duration(req: SipGoalRequest):
    """
    Given a monthly SIP and target, returns the number of months/years needed.
    """
    from financial_engine.sip_calculator import months_to_goal
    if not req.monthly_sip:
        raise HTTPException(status_code=400, detail="'monthly_sip' is required for this calculation")
    return months_to_goal(req.target_amount, req.monthly_sip, cagr=req.cagr,
                          existing_corpus=req.existing_corpus)


# ── Fund allocation ───────────────────────────────────────────────────────────

@app.post("/sip/split", tags=["SIP Advisor"],
          summary="Split SIP across specific named funds with exact INR amounts")
def sip_split(req: SipSplitRequest):
    """
    Returns a fund-by-fund allocation:
      - Fund name, house, category
      - INR amount per month
      - Percentage weight
      - 5yr return, expense ratio, min SIP
      - Blended CAGR across the portfolio
    """
    from financial_engine.fund_allocator import allocate_sip
    return allocate_sip(req.monthly_sip, risk_level=req.risk_level,
                        goal_type=req.goal_type, horizon_years=req.horizon_years,
                        prefer_low_cost=req.prefer_low_cost,
                        existing_sip_funds=req.existing_sip_funds)


# ── Full plan ─────────────────────────────────────────────────────────────────

@app.post("/sip/plan", tags=["SIP Advisor"],
          summary="Complete SIP plan: fund split + corpus projection + goal analysis")
def sip_full_plan(req: SipPlanRequest):
    """
    One API call answering all 5 questions:
    1. Which fund gets how much SIP
    2. Projected corpus (flat + step-up)
    3. Per-fund corpus projections
    4. SIP needed to reach goal
    5. Duration to reach goal at current SIP
    """
    from financial_engine.sip_advisor import full_sip_plan
    return full_sip_plan(
        monthly_sip        = req.monthly_sip,
        goal_type          = req.goal_type,
        goal_amount        = req.goal_amount,
        horizon_years      = req.horizon_years,
        risk_level         = req.risk_level,
        step_up_pct        = req.step_up_pct,
        existing_corpus    = req.existing_corpus,
        prefer_low_cost    = req.prefer_low_cost,
        existing_sip_funds = req.existing_sip_funds,
    )


# ── Fund comparison ───────────────────────────────────────────────────────────

@app.post("/funds/compare", tags=["Fund Comparison"],
          summary="Compare Fund A vs Fund B: corpus, expense drag, goal hit")
def funds_compare(req: FundCompareRequest):
    """
    Side-by-side comparison of 2+ funds:
      - Projected gross and net corpus (after expense drag)
      - Wealth multiplier
      - Risk-adjusted return
      - Whether each fund hits the goal amount
      - Corpus gap/surplus vs goal
      - SIP amount needed (per fund) to hit goal on time
    """
    from financial_engine.fund_comparator import compare_funds
    return compare_funds(
        fund_queries    = req.fund_queries,
        monthly_sip     = req.monthly_sip,
        years           = req.years,
        goal_amount     = req.goal_amount,
        existing_corpus = req.existing_corpus,
        step_up_pct     = req.step_up_pct,
    )


# ── Fund database ─────────────────────────────────────────────────────────────

@app.get("/funds", tags=["Fund Comparison"],
         summary="List all funds in the database")
def list_funds(category: Optional[str] = None, fund_type: Optional[str] = None):
    """
    Browse the fund database.
    Filter by category (large_cap, mid_cap, debt, liquid, gold, elss, …)
    or fund_type (equity, debt, hybrid, commodity).
    """
    from financial_engine.fund_database import FUNDS, CATEGORY_MAP
    funds = FUNDS
    if category:
        keys  = CATEGORY_MAP.get(category, [category])
        funds = [f for f in funds if f["category"] in keys]
    if fund_type:
        funds = [f for f in funds if f["fund_type"] == fund_type]
    return {"count": len(funds), "funds": funds}


@app.get("/funds/{fund_id}", tags=["Fund Comparison"],
         summary="Get details for a specific fund by id")
def get_fund(fund_id: str):
    from financial_engine.fund_database import get_fund_by_id
    fund = get_fund_by_id(fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund '{fund_id}' not found")
    return fund
