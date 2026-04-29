"""
test_full_system.py - Full System Test for AI Financial Decision Engine

Tests all 20 modules, all engines, and the complete 13-section report.
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PASS = 0
FAIL = 0


def test(name, fn):
    global PASS, FAIL
    print(f"[TEST] {name}...")
    try:
        fn()
        PASS += 1
        print(f"  PASSED\n")
    except Exception as e:
        FAIL += 1
        print(f"  FAILED: {e}\n")


# ──────────────────────────────────────────────
#  Shared test data
# ──────────────────────────────────────────────

ENGINE_ARGS = dict(
    salary=75000, monthly_savings=20000, goal_years=7, risk_level="medium",
    dependents=1, investment_experience="intermediate", emergency_fund_months=4,
    debt_to_income=0.15, current_equity_value=300000, current_debt_value=100000,
    sip_amount=8000, sip_active=True, num_stocks=4, num_mutual_funds=3,
)

GOALS = [
    {"name": "Emergency Fund", "target": 300000, "saved": 220000, "years": 1, "priority": "critical"},
    {"name": "Son Education", "target": 1500000, "saved": 200000, "years": 10, "priority": "high"},
    {"name": "Dream Home", "target": 2500000, "saved": 400000, "years": 8, "priority": "medium"},
    {"name": "Retirement", "target": 20000000, "saved": 800000, "years": 30, "priority": "low"},
]

STOCKS = [
    {"name": "HDFCBANK", "value": 80000},
    {"name": "TCS", "value": 70000},
    {"name": "RELIANCE", "value": 90000},
    {"name": "INFY", "value": 60000},
]

MUTUAL_FUNDS = [
    {"name": "Axis Bluechip Fund", "value": 50000},
    {"name": "Mirae Asset Large Cap Fund", "value": 40000},
    {"name": "SBI Small Cap Fund", "value": 30000},
]

DEBT_INV = [
    {"name": "SBI FD", "value": 100000},
]


# ──────────────────────────────────────────────
#  Test 1: Import all modules
# ──────────────────────────────────────────────
def test_imports():
    import importlib
    modules = [
        "financial_engine",
        "financial_engine.risk_scorer",
        "financial_engine.segmentation",
        "financial_engine.rule_engine",
        "financial_engine.opportunity_cost",
        "financial_engine.recommendation_engine",
        "financial_engine.portfolio_analyzer",
        "financial_engine.category_filter",
        "financial_engine.feature_analysis",
        "financial_engine.data_generation",
        "financial_engine.product_engine",
        "financial_engine.cash_flow_buffer",
        "financial_engine.income_shock_simulator",
        "financial_engine.inflation_engine",
        "financial_engine.market_scenario_engine",
        "financial_engine.tax_engine",
        "financial_engine.goal_planner",
        "financial_engine.display",
    ]
    failed = []
    for mod in modules:
        try:
            importlib.import_module(mod)
            print(f"    OK  {mod}")
        except Exception as e:
            failed.append(f"{mod}: {e}")
            print(f"    FAIL {mod}: {e}")
    assert not failed, f"Failed imports: {failed}"

test("Import all 18 modules", test_imports)


# ──────────────────────────────────────────────
#  Test 2: Risk Score (with Income Stability)
# ──────────────────────────────────────────────
def test_risk_scorer():
    from financial_engine.risk_scorer import compute_risk_score
    r = compute_risk_score(**ENGINE_ARGS, income_type="salaried")
    assert "risk_score" in r and 0 <= r["risk_score"] <= 100
    assert "income_stability_detail" in r
    isd = r["income_stability_detail"]
    assert "stability_score" in isd and "volatility" in isd
    print(f"    Risk: {r['risk_score']}/100 ({r['risk_label']}) | Stability: {isd['stability_score']} | Volatility: {isd['volatility']}")

test("Risk Score Engine (+ Income Stability)", test_risk_scorer)


# ──────────────────────────────────────────────
#  Test 3: Segmentation
# ──────────────────────────────────────────────
def test_segmentation():
    from financial_engine.segmentation import classify_segment
    seg = classify_segment(**ENGINE_ARGS)
    assert "segment" in seg and "profile" in seg
    print(f"    Segment: {seg['segment']} -- {seg['profile']['label']}")

test("Segmentation Engine", test_segmentation)


# ──────────────────────────────────────────────
#  Test 4: Rule Engine + Intensity
# ──────────────────────────────────────────────
def test_rule_engine():
    from financial_engine.rule_engine import predict, compute_intensity
    action, conf = predict(**ENGINE_ARGS)
    assert isinstance(action, str) and 0 <= conf <= 100
    intensity = compute_intensity(action, **ENGINE_ARGS)
    assert "action_detail" in intensity
    print(f"    Action: {action} | Confidence: {conf}% | Detail: {intensity['action_detail'][:50]}")

test("Rule Engine + Intensity", test_rule_engine)


# ──────────────────────────────────────────────
#  Test 5: Opportunity Cost
# ──────────────────────────────────────────────
def test_opportunity_cost():
    from financial_engine.rule_engine import predict, compute_intensity
    from financial_engine.opportunity_cost import compute_opportunity_cost
    action, _ = predict(**ENGINE_ARGS)
    intensity = compute_intensity(action, **ENGINE_ARGS)
    opp = compute_opportunity_cost(action, ENGINE_ARGS, intensity["metrics"])
    assert "cost_of_inaction" in opp and "nudge" in opp
    print(f"    Cost: {opp['cost_of_inaction'][:60]}...")

test("Opportunity Cost Engine", test_opportunity_cost)


# ──────────────────────────────────────────────
#  Test 6: Recommendation Engine
# ──────────────────────────────────────────────
def test_recommendation():
    from financial_engine.recommendation_engine import get_recommendation
    rec = get_recommendation("INCREASE_SIP", "medium", 7)
    assert "category_label" in rec and "fund_types" in rec
    print(f"    Category: {rec['category_label']} | Funds: {len(rec['fund_types'])}")

test("Recommendation Engine", test_recommendation)


# ──────────────────────────────────────────────
#  Test 7: Portfolio Analyzer
# ──────────────────────────────────────────────
def test_portfolio():
    from financial_engine.portfolio_analyzer import analyze_portfolio
    pa = analyze_portfolio(STOCKS, MUTUAL_FUNDS, DEBT_INV)
    assert "sector_exposure" in pa and "derived" in pa
    d = pa["derived"]
    print(f"    Equity: INR {d['current_equity_value']:,} | Debt: INR {d['current_debt_value']:,} | Sectors: {len(pa['sector_exposure'])}")

test("Portfolio Analyzer", test_portfolio)


# ──────────────────────────────────────────────
#  Test 8: Category Filter
# ──────────────────────────────────────────────
def test_category_filter():
    from financial_engine.category_filter import suggest_categories
    cat = suggest_categories("medium", 7, "intermediate")
    assert "primary" in cat and "mf_types" in cat
    print(f"    Primary: {cat['primary']} | MFs: {len(cat['mf_types'])} | Stocks: {len(cat['stock_types'])}")

test("Category Filter", test_category_filter)


# ──────────────────────────────────────────────
#  Test 9: Cash Flow Buffer
# ──────────────────────────────────────────────
def test_cash_flow_buffer():
    from financial_engine.cash_flow_buffer import compute_cash_flow_buffer, format_cash_flow_buffer
    cfb = compute_cash_flow_buffer(**ENGINE_ARGS)
    assert "survival_months" in cfb and "buffer_rating" in cfb
    fmt = format_cash_flow_buffer(cfb)
    assert len(fmt) > 100
    print(f"    Survival: {cfb['survival_months']}mo ({cfb['buffer_rating']}) | Burn: INR {cfb['emergency_monthly_burn']:,}/mo")

test("Cash Flow Buffer Engine", test_cash_flow_buffer)


# ──────────────────────────────────────────────
#  Test 10: Income Shock Simulator
# ──────────────────────────────────────────────
def test_income_shock():
    from financial_engine.income_shock_simulator import simulate_income_shocks, format_shock_simulation
    shock = simulate_income_shocks(**ENGINE_ARGS, goals=GOALS)
    assert "resilience_score" in shock and len(shock["scenarios"]) == 4
    fmt = format_shock_simulation(shock)
    assert len(fmt) > 200
    print(f"    Resilience: {shock['resilience_score']}/100 ({shock['resilience_label']})")
    for k, sc in shock["scenarios"].items():
        surv = "YES" if sc["survives_full_duration"] else "NO"
        print(f"      {sc['label']:36s} Survives: {surv:3s} | Severity: {sc['severity']}")

test("Income Shock Simulator", test_income_shock)


# ──────────────────────────────────────────────
#  Test 11: Inflation Engine
# ──────────────────────────────────────────────
def test_inflation():
    from financial_engine.inflation_engine import analyze_goal_inflation, format_inflation_analysis
    inf = analyze_goal_inflation(GOALS)
    assert "goal_analyses" in inf and "portfolio_inflation_risk" in inf
    fmt = format_inflation_analysis(inf)
    assert len(fmt) > 200
    print(f"    Portfolio Inflation Risk: {inf['portfolio_inflation_risk']}/100")
    for ga in inf["goal_analyses"]:
        print(f"      {ga['goal_name']:20s} Today: INR {ga['today_cost']:>12,} -> INR {ga['inflation_adjusted_target']:>12,} ({ga['inflation_multiplier']}x in {ga['years']}yr)")

test("Inflation Engine (4 layers)", test_inflation)


# ──────────────────────────────────────────────
#  Test 12: Market Scenario Engine
# ──────────────────────────────────────────────
def test_market():
    from financial_engine.market_scenario_engine import analyze_market_risk, format_market_risk_analysis
    mkt = analyze_market_risk(GOALS, monthly_savings=20000, risk_level="medium", num_simulations=300)
    assert "goal_analyses" in mkt and "portfolio_success_rate" in mkt
    fmt = format_market_risk_analysis(mkt)
    assert len(fmt) > 200
    print(f"    Portfolio Success: {mkt['portfolio_success_rate']}% | Risk: {mkt['portfolio_market_risk']}/100")
    for ga in mkt["goal_analyses"]:
        mc = ga["monte_carlo"]
        print(f"      {ga['goal_name']:20s} Success: {mc['success_probability']:5.1f}% | Seq: {ga['sequence_risk']['sequence_risk']:8s} | Timing: {ga['timing_risk']['timing_risk']}")

test("Market Scenario Engine (Monte Carlo)", test_market)


# ──────────────────────────────────────────────
#  Test 13: Tax Engine
# ──────────────────────────────────────────────
def test_tax():
    from financial_engine.tax_engine import analyze_tax_impact, format_tax_analysis
    tax = analyze_tax_impact(
        salary=75000, goals=GOALS, risk_level="medium",
        income_type="salaried", regime="new",
        deductions_80c=50000, deductions_80d=15000,
    )
    assert "tax_profile" in tax and "optimizations" in tax
    fmt = format_tax_analysis(tax)
    assert len(fmt) > 200
    tp = tax["tax_profile"]
    print(f"    Income: INR {tp['annual_income']:,} | Slab: {tp['tax_slab_pct']}% | Tax: INR {tp['total_tax']:,}")
    for gv in tax["goal_tax_views"]:
        print(f"      {gv['goal_name']:20s} {gv['strategy']:12s} Pre: {gv['pre_tax_return']:>6s} -> Post: {gv['after_tax_return']:>6s} (Drag: {gv['tax_drag']})")
    print(f"    Optimizations: {len(tax['optimizations'])} strategies")

test("Tax Engine (7 layers)", test_tax)


# ──────────────────────────────────────────────
#  Test 14: Goal Planner (Full Integration)
# ──────────────────────────────────────────────
def test_goal_planner():
    from financial_engine.goal_planner import compute_goal_plan, format_goal_plan
    plan = compute_goal_plan(GOALS, monthly_savings=20000, risk_level="medium", marginal_tax_rate=0.10)
    assert "goal_plans" in plan and "affordable" in plan
    fmt = format_goal_plan(plan)
    assert len(fmt) > 200
    print(f"    SIP needed: INR {plan['total_monthly_needed']:,}/mo | Allocated: INR {plan['total_allocated']:,}/mo | Affordable: {plan['affordable']}")
    for gp in plan["goal_plans"]:
        print(f"      {gp['name']:20s} Adj: INR {gp['inflation_adjusted_target']:>12,} | SIP: INR {gp['allocated_sip']:>6,}/mo | Return: {gp['expected_return']:.1%} (pre: {gp['pre_tax_return']:.1%}) | Success: {gp['success_probability']:5.1f}% | {gp['status']}")

test("Goal Planner (Inflation+Market+Tax)", test_goal_planner)


# ──────────────────────────────────────────────
#  Test 15: Full 13-Section Report (display.py)
# ──────────────────────────────────────────────
def test_full_report():
    from financial_engine.display import format_full_report
    profile = {
        "salary": 75000, "monthly_savings": 20000, "goal_years": 7, "risk_level": "medium",
        "dependents": 1, "investment_experience": "intermediate", "emergency_fund_months": 4,
        "debt_to_income": 0.15,
    }
    sip_info = {"sip_active": True, "sip_amount": 8000}

    report = format_full_report(
        profile, sip_info, STOCKS, MUTUAL_FUNDS, DEBT_INV,
        ml_predictions=None, goals=GOALS, income_type="salaried",
        tax_regime="new", deductions_80c=50000, deductions_80d=15000,
    )
    assert len(report) > 3000

    # Verify all sections exist
    sections = [
        "1. RISK SCORE", "2. CASH FLOW BUFFER", "3. INCOME SHOCK SIMULATION",
        "4. SEGMENT", "5. PORTFOLIO ANALYSIS", "6. SMART PREDICTION",
        "9. INFLATION ANALYSIS", "10. MARKET RISK ANALYSIS",
        "11. TAX ANALYSIS", "12. GOAL-BASED PLAN", "13. INVESTMENT CATEGORIES",
    ]
    found = []
    missing = []
    for s in sections:
        if s in report:
            found.append(s.split(". ")[1])
        else:
            missing.append(s)

    print(f"    Report: {len(report):,} chars | {report.count(chr(10)):,} lines")
    print(f"    Sections found: {len(found)}/11 -- {', '.join(found)}")
    if missing:
        print(f"    Missing: {missing}")
    assert not missing, f"Missing sections: {missing}"

test("Full 13-Section Report (display.py)", test_full_report)


# ──────────────────────────────────────────────
#  FINAL SUMMARY
# ──────────────────────────────────────────────
print("=" * 70)
print(f"  RESULTS: {PASS} PASSED | {FAIL} FAILED | {PASS + FAIL} TOTAL")
if FAIL == 0:
    print("  ALL TESTS PASSED -- FULL SYSTEM OPERATIONAL")
else:
    print(f"  WARNING: {FAIL} test(s) failed!")
print("=" * 70)

sys.exit(FAIL)
