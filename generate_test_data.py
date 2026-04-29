"""
generate_test_data.py - Generate 1000 realistic test profiles with itemized holdings.
Outputs: test_profiles.csv (flat for ML testing) + test_profiles_detailed.json (itemized)
"""

import random
import json
import csv

random.seed(42)

STOCK_POOL = [
    ("HDFC Bank", "Banking"), ("ICICI Bank", "Banking"), ("SBI", "Banking"),
    ("Kotak Bank", "Banking"), ("Axis Bank", "Banking"),
    ("TCS", "IT"), ("Infosys", "IT"), ("Wipro", "IT"), ("HCL Tech", "IT"),
    ("Sun Pharma", "Pharma"), ("Dr Reddy's", "Pharma"), ("Cipla", "Pharma"),
    ("HUL", "FMCG"), ("ITC", "FMCG"), ("Nestle", "FMCG"),
    ("Maruti", "Auto"), ("Tata Motors", "Auto"), ("M&M", "Auto"),
    ("Reliance", "Conglomerate"), ("L&T", "Infrastructure"),
    ("NTPC", "Power"), ("Airtel", "Telecom"),
    ("Tata Steel", "Metals"), ("UltraTech", "Cement"),
]

MF_POOL = [
    ("HDFC Index Fund", "equity"), ("UTI Nifty 50 Index Fund", "equity"),
    ("Mirae Asset Large Cap", "equity"), ("Axis Bluechip Fund", "equity"),
    ("Kotak Emerging Equity", "equity"), ("Axis Midcap Fund", "equity"),
    ("SBI Small Cap Fund", "equity"), ("Nippon India Small Cap", "equity"),
    ("Parag Parikh Flexi Cap", "equity"), ("HDFC Flexi Cap", "equity"),
    ("Motilal Oswal Nasdaq 100", "equity"),
    ("ICICI Pru BAF", "hybrid"), ("HDFC BAF", "hybrid"),
    ("HDFC Short Term Debt", "debt"), ("ICICI Pru Corporate Bond", "debt"),
    ("SBI Magnum Gilt", "debt"),
]

DEBT_POOL = [
    ("PPF", "debt"), ("FD", "debt"), ("NPS", "hybrid"),
    ("HDFC Liquid Fund", "debt"), ("Parag Parikh Liquid", "debt"),
]

RISK_LEVELS = ["low", "medium", "high"]
EXPERIENCE = ["beginner", "intermediate", "expert"]


def generate_one(idx):
    salary = random.randint(20000, 100000)
    savings = random.randint(2000, min(50000, int(salary * 0.6)))
    goal_years = random.randint(1, 15)
    risk = random.choice(RISK_LEVELS)
    dependents = random.randint(0, 5)
    experience = random.choice(EXPERIENCE)
    emergency = random.randint(0, 12)
    dti = round(random.uniform(0, 0.6), 2)
    sip_active = random.choice([True, False])
    sip_amount = random.randint(500, min(25000, int(salary * 0.3))) if sip_active else 0

    # Generate itemized holdings
    num_stocks = random.randint(0, 8)
    num_mf = random.randint(0, 6)
    num_debt = random.randint(0, 3)

    stocks = []
    chosen_stocks = random.sample(STOCK_POOL, min(num_stocks, len(STOCK_POOL)))
    for name, sector in chosen_stocks:
        stocks.append({"name": name, "value": random.randint(5000, 200000)})

    mutual_funds = []
    chosen_mf = random.sample(MF_POOL, min(num_mf, len(MF_POOL)))
    for name, mf_type in chosen_mf:
        mutual_funds.append({"name": name, "value": random.randint(5000, 100000)})

    debt_investments = []
    chosen_debt = random.sample(DEBT_POOL, min(num_debt, len(DEBT_POOL)))
    for name, d_type in chosen_debt:
        debt_investments.append({"name": name, "value": random.randint(5000, 100000)})

    # Compute flat values
    stock_value = sum(s["value"] for s in stocks)
    mf_value = sum(f["value"] for f in mutual_funds)
    debt_value = sum(d["value"] for d in debt_investments)
    equity_value = stock_value + int(mf_value * 0.7)
    total_debt = debt_value + int(mf_value * 0.3)
    portfolio_total = equity_value + total_debt

    return {
        "id": idx,
        "salary": salary,
        "monthly_savings": savings,
        "goal_years": goal_years,
        "risk_level": risk,
        "dependents": dependents,
        "investment_experience": experience,
        "emergency_fund_months": emergency,
        "debt_to_income": dti,
        "sip_active": sip_active,
        "sip_amount": sip_amount,
        "stocks": stocks,
        "mutual_funds": mutual_funds,
        "debt_investments": debt_investments,
        # Flat (for CSV)
        "num_stocks": len(stocks),
        "num_mutual_funds": len(mutual_funds),
        "current_equity_value": equity_value,
        "current_debt_value": max(1, total_debt),
        "stock_value": stock_value,
        "mf_value": mf_value,
        "debt_inv_value": debt_value,
        "portfolio_total": portfolio_total,
    }


def main():
    profiles = [generate_one(i + 1) for i in range(1000)]

    # ── Save detailed JSON (with itemized holdings) ──
    json_data = []
    for p in profiles:
        json_data.append({
            "id": p["id"],
            "salary": p["salary"],
            "monthly_savings": p["monthly_savings"],
            "goal_years": p["goal_years"],
            "risk_level": p["risk_level"],
            "dependents": p["dependents"],
            "investment_experience": p["investment_experience"],
            "emergency_fund_months": p["emergency_fund_months"],
            "debt_to_income": p["debt_to_income"],
            "sip_active": p["sip_active"],
            "sip_amount": p["sip_amount"],
            "stocks": p["stocks"],
            "mutual_funds": p["mutual_funds"],
            "debt_investments": p["debt_investments"],
        })

    with open("test_profiles_detailed.json", "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"Saved test_profiles_detailed.json ({len(json_data)} profiles)")

    # ── Save flat CSV (for ML model testing) ──
    csv_fields = [
        "id", "salary", "monthly_savings", "goal_years", "risk_level",
        "dependents", "investment_experience", "emergency_fund_months",
        "debt_to_income", "sip_active", "sip_amount",
        "num_stocks", "num_mutual_funds",
        "current_equity_value", "current_debt_value",
        "stock_value", "mf_value", "debt_inv_value", "portfolio_total",
    ]

    with open("test_profiles.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for p in profiles:
            writer.writerow({k: p[k] for k in csv_fields})
    print(f"Saved test_profiles.csv ({len(profiles)} rows, {len(csv_fields)} columns)")


if __name__ == "__main__":
    main()
