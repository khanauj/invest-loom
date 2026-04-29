"""
run_demo.py - Full 13-Section Report Demo

Client: Priya Mehta, 32, Senior Software Engineer, Mumbai
Income: INR 95,000/mo | Savings: INR 28,000/mo | SIP: INR 10,000/mo
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from financial_engine.display import format_full_report

# ══════════════════════════════════════════════════════════════
#  CLIENT PROFILE: Priya Mehta
# ══════════════════════════════════════════════════════════════

profile = {
    "salary": 95000,
    "monthly_savings": 28000,
    "goal_years": 5,
    "risk_level": "medium",
    "dependents": 2,
    "investment_experience": "intermediate",
    "emergency_fund_months": 3,
    "debt_to_income": 0.25,
}

sip_info = {
    "sip_active": True,
    "sip_amount": 10000,
}

stocks = [
    {"name": "HDFC Bank",   "quantity": 164, "price": 731.55},   # 164 × ₹731.55  ≈ ₹1,19,974
    {"name": "TCS",         "quantity":  40, "price": 2358.90},  #  40 × ₹2,358.90 ≈ ₹ 94,356
    {"name": "Reliance",    "quantity":  82, "price": 1343.90},  #  82 × ₹1,343.90 ≈ ₹1,10,200
    {"name": "Infosys",     "quantity": 100, "price": 750.00},   # 100 × ₹750.00   ≈ ₹ 75,000
    {"name": "ICICI Bank",  "quantity":  82, "price": 731.55},   #  82 × ₹731.55   ≈ ₹ 59,987
]

mutual_funds = [
    {"name": "Axis Bluechip Fund", "value": 80000},
    {"name": "Mirae Asset Large Cap Fund", "value": 60000},
    {"name": "Parag Parikh Flexi Cap Fund", "value": 45000},
    {"name": "SBI Small Cap Fund", "value": 35000},
]

debt_investments = [
    {"name": "SBI FD", "value": 150000},
    {"name": "PPF", "value": 200000},
]

goals = [
    {"name": "Emergency Fund",       "target": 400000,   "saved": 180000, "years": 1,  "priority": "critical"},
    {"name": "Daughter Education",   "target": 2000000,  "saved": 300000, "years": 8,  "priority": "high"},
    {"name": "Family Vacation Europe", "target": 500000, "saved": 50000,  "years": 2,  "priority": "medium"},
    {"name": "House Down Payment",   "target": 3000000,  "saved": 500000, "years": 7,  "priority": "medium"},
    {"name": "Retirement Corpus",    "target": 30000000, "saved": 1200000,"years": 28, "priority": "low"},
]

# ══════════════════════════════════════════════════════════════
#  RUN FULL REPORT
# ══════════════════════════════════════════════════════════════

print("=" * 90)
print("  AI FINANCIAL DECISION ENGINE -- COMPLETE ADVISORY REPORT")
print("  Client: Priya Mehta | Age: 32 | Sr. Software Engineer, Mumbai")
print("  Generated: 2026-03-27 | Engine: v2.0 | Sections: 13")
print("=" * 90)
print()

report = format_full_report(
    profile=profile,
    sip_info=sip_info,
    stocks=stocks,
    mutual_funds=mutual_funds,
    debt_investments=debt_investments,
    ml_predictions=None,
    goals=goals,
    income_type="salaried",
    tax_regime="new",
    deductions_80c=80000,       # PPF + LIC
    deductions_80d=20000,       # Health insurance
    hra_claimed=0,
    existing_elss=30000,
)

print(report)

print()
print("=" * 90)
print("  All deterministic. Zero LLM. Zero API cost. Pure math + rules + simulation.")
print("  Engines: Risk | Buffer | Shock | Segment | Portfolio | Prediction | Ensemble")
print("           Inflation | Market (Monte Carlo) | Tax | Goal Planner | Categories")
print("=" * 90)
