"""
run_test.py - Test all 1000 profiles through the full system.
Outputs: test_results.csv with action, confidence, risk, segment, warnings.
"""

import json
import csv
import requests
import time

API = "http://127.0.0.1:8000"

with open("test_profiles_detailed.json") as f:
    profiles = json.load(f)

print(f"Testing {len(profiles)} profiles against {API}/predict/smart ...")
print()

results = []
errors = 0
start = time.time()

action_counts = {}
segment_counts = {}
risk_dist = {"very_low": 0, "low": 0, "moderate": 0, "high": 0, "very_high": 0}
warning_count = 0
duplicate_count = 0

for i, p in enumerate(profiles):
    try:
        resp = requests.post(f"{API}/predict/smart", json=p, timeout=10)
        if resp.status_code != 200:
            errors += 1
            results.append({"id": p["id"], "error": resp.text[:100]})
            continue

        d = resp.json()
        action = d["action"]
        conf = d["confidence"]
        ctx = d["context"]
        warns = len(d["portfolio_analysis"]["concentration_warnings"])
        dups = len(d["portfolio_analysis"]["duplicates"])
        gaps = len(d["portfolio_analysis"]["gaps"].get("missing_fund_categories", []))
        suggestions = len(d["smart_suggestions"])

        action_counts[action] = action_counts.get(action, 0) + 1
        segment_counts[ctx["segment_label"]] = segment_counts.get(ctx["segment_label"], 0) + 1
        risk_dist[ctx["risk_label"]] = risk_dist.get(ctx["risk_label"], 0) + 1
        if warns > 0: warning_count += 1
        if dups > 0: duplicate_count += 1

        results.append({
            "id": p["id"],
            "action": action,
            "action_detail": d["action_detail"],
            "confidence": conf,
            "risk_score": ctx["risk_score"],
            "risk_label": ctx["risk_label"],
            "segment": ctx["segment_label"],
            "equity_pct": ctx["equity_pct"],
            "portfolio_total": ctx["portfolio_total"],
            "num_stocks": ctx["num_stocks"],
            "num_mutual_funds": ctx["num_mutual_funds"],
            "concentration_warnings": warns,
            "duplicates": dups,
            "gaps": gaps,
            "smart_suggestions": suggestions,
        })

    except Exception as e:
        errors += 1
        results.append({"id": p["id"], "error": str(e)[:100]})

    if (i + 1) % 100 == 0:
        elapsed = time.time() - start
        print(f"  [{i+1}/1000] {elapsed:.1f}s elapsed, {errors} errors")

elapsed = time.time() - start
print()
print(f"Done in {elapsed:.1f}s ({len(profiles)/elapsed:.0f} profiles/sec)")
print(f"Success: {len(profiles) - errors} | Errors: {errors}")

# Save CSV
csv_fields = [
    "id", "action", "action_detail", "confidence", "risk_score", "risk_label",
    "segment", "equity_pct", "portfolio_total", "num_stocks", "num_mutual_funds",
    "concentration_warnings", "duplicates", "gaps", "smart_suggestions",
]
with open("test_results.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
    writer.writeheader()
    for r in results:
        if "error" not in r:
            writer.writerow(r)

good = len(profiles) - errors
print(f"\nSaved test_results.csv ({good} rows)")

# Print summary
print()
print("=" * 60)
print("  TEST SUMMARY — 1000 PROFILES")
print("=" * 60)

print("\n  ACTION DISTRIBUTION:")
for a, c in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
    bar = "#" * (c // 5)
    print(f"    {a:25s} {c:4d}  {bar}")

print("\n  SEGMENT DISTRIBUTION:")
for s, c in sorted(segment_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"    {s:25s} {c:4d}")

print("\n  RISK DISTRIBUTION:")
for r, c in sorted(risk_dist.items(), key=lambda x: x[1], reverse=True):
    print(f"    {r:15s} {c:4d}")

print(f"\n  PORTFOLIO HEALTH:")
print(f"    Profiles with concentration warnings: {warning_count}/1000 ({warning_count/10:.0f}%)")
print(f"    Profiles with duplicate holdings:     {duplicate_count}/1000 ({duplicate_count/10:.0f}%)")
print(f"    Average suggestions per profile:      {sum(r.get('smart_suggestions',0) for r in results if 'error' not in r) / max(1,good):.1f}")
print("=" * 60)
