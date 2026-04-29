"""
feature_analysis.py - Post-Tree Feature Principal Analysis (FPA)

Runs AFTER PART builds its rules. Analyzes:
  1. Feature importance — which features appear in rules, how often, weighted by coverage
  2. Unused features — features PART never split on (candidates for removal)
  3. Feature correlation — pairs with high correlation (redundant information)
  4. Per-action feature drivers — which features matter most for each action
  5. Threshold analysis — what split points PART chose for each feature

No LLM. Pure analysis of the learned PART rules + training data.
"""

import numpy as np
import pandas as pd
from collections import defaultdict


def analyze_part_features(part_model, X_train=None):
    """
    Full feature analysis on a trained PART model.

    Args:
        part_model: trained PARTClassifier
        X_train: training data (DataFrame or numpy array) for correlation analysis.
                 Optional — if None, correlation analysis is skipped.

    Returns dict with:
        feature_importance: sorted list of {name, rule_count, coverage_weighted, pct, rank}
        unused_features: list of feature names never used in any rule
        action_drivers: dict action -> list of top features driving that action
        thresholds: dict feature -> list of {operator, threshold, action, coverage}
        correlations: list of {feat1, feat2, correlation} for high-correlation pairs
        summary: dict with counts and key stats
    """
    rules = part_model.rules
    all_features = part_model.feature_names
    total_rules = len(rules)

    # ── 1. Feature Importance ──
    feat_rule_count = defaultdict(int)       # how many rules use this feature
    feat_coverage = defaultdict(int)         # total coverage of rules using this feature
    feat_weighted = defaultdict(float)       # coverage × accuracy weighted

    for rule in rules:
        features_in_rule = set()
        for feat_idx, op, threshold, feat_name in rule.conditions:
            features_in_rule.add(feat_name)

        for feat_name in features_in_rule:
            feat_rule_count[feat_name] += 1
            feat_coverage[feat_name] += rule.coverage
            feat_weighted[feat_name] += rule.coverage * rule.accuracy

    # Normalize weighted scores
    max_weighted = max(feat_weighted.values()) if feat_weighted else 1
    importance = []
    for feat in all_features:
        rc = feat_rule_count.get(feat, 0)
        cov = feat_coverage.get(feat, 0)
        wt = feat_weighted.get(feat, 0)
        normalized = round(wt / max_weighted * 100, 1) if max_weighted > 0 else 0

        # Rank label
        if rc == 0:
            rank = "UNUSED"
        elif normalized >= 60:
            rank = "HIGH"
        elif normalized >= 30:
            rank = "MEDIUM"
        elif normalized >= 10:
            rank = "LOW"
        else:
            rank = "MINIMAL"

        importance.append({
            "name": feat,
            "rule_count": rc,
            "total_rules": total_rules,
            "coverage": cov,
            "weighted_score": round(normalized, 1),
            "rank": rank,
        })

    importance.sort(key=lambda x: x["weighted_score"], reverse=True)

    # ── 2. Unused Features ──
    unused = [f["name"] for f in importance if f["rule_count"] == 0]

    # ── 3. Per-Action Feature Drivers ──
    action_features = defaultdict(lambda: defaultdict(int))
    for rule in rules:
        action = rule.class_name
        for feat_idx, op, threshold, feat_name in rule.conditions:
            action_features[action][feat_name] += 1

    action_drivers = {}
    for action, feats in action_features.items():
        sorted_feats = sorted(feats.items(), key=lambda x: x[1], reverse=True)
        action_drivers[action] = [{"feature": f, "count": c} for f, c in sorted_feats]

    # ── 4. Threshold Analysis ──
    thresholds = defaultdict(list)
    for rule in rules:
        for feat_idx, op, threshold, feat_name in rule.conditions:
            thresholds[feat_name].append({
                "operator": op,
                "threshold": threshold,
                "action": rule.class_name,
                "coverage": rule.coverage,
                "accuracy": rule.accuracy,
            })

    # Sort thresholds by threshold value
    for feat in thresholds:
        thresholds[feat].sort(key=lambda x: x["threshold"])

    # ── 5. Correlation Analysis ──
    correlations = []
    if X_train is not None:
        if isinstance(X_train, pd.DataFrame):
            corr_matrix = X_train.corr()
        else:
            df_temp = pd.DataFrame(X_train, columns=all_features)
            corr_matrix = df_temp.corr()

        for i, f1 in enumerate(all_features):
            for j, f2 in enumerate(all_features):
                if i < j:
                    corr = abs(corr_matrix.loc[f1, f2])
                    if corr >= 0.5:  # only report meaningful correlations
                        correlations.append({
                            "feature_1": f1,
                            "feature_2": f2,
                            "correlation": round(corr, 3),
                            "redundant": corr >= 0.85,
                        })

        correlations.sort(key=lambda x: x["correlation"], reverse=True)

    # ── Summary ──
    used_count = sum(1 for f in importance if f["rule_count"] > 0)
    high_count = sum(1 for f in importance if f["rank"] == "HIGH")

    summary = {
        "total_features": len(all_features),
        "used_features": used_count,
        "unused_features": len(unused),
        "high_importance": high_count,
        "total_rules": total_rules,
        "high_correlation_pairs": len([c for c in correlations if c["redundant"]]),
    }

    return {
        "feature_importance": importance,
        "unused_features": unused,
        "action_drivers": dict(action_drivers),
        "thresholds": dict(thresholds),
        "correlations": correlations,
        "summary": summary,
    }


def format_feature_analysis(analysis, user_input=None):
    """
    Format FPA results for display.

    Args:
        analysis: dict from analyze_part_features()
        user_input: optional user profile dict to highlight which features
                    are driving THIS user's prediction

    Returns: formatted string
    """
    lines = []
    imp = analysis["feature_importance"]
    summary = analysis["summary"]

    lines.append(f"  FEATURE ANALYSIS (from PART rules)")
    lines.append(f"  {summary['used_features']}/{summary['total_features']} features used across {summary['total_rules']} rules")
    lines.append("")

    # Feature importance table
    lines.append(f"  {'Feature':26s} {'Rules':>6s}  {'Score':>6s}  {'Rank':8s}  Bar")
    lines.append("  " + "-" * 70)

    for f in imp:
        bar_len = int(f["weighted_score"] / 10)
        bar = "#" * bar_len + "." * (10 - bar_len)
        rules_str = f"{f['rule_count']}/{f['total_rules']}"
        lines.append(f"  {f['name']:26s} {rules_str:>6s}  {f['weighted_score']:5.1f}%  {f['rank']:8s}  {bar}")

    # Unused features
    if analysis["unused_features"]:
        lines.append("")
        lines.append(f"  UNUSED FEATURES ({len(analysis['unused_features'])}):")
        lines.append(f"    {', '.join(analysis['unused_features'])}")
        lines.append("    -> These features had no impact on PART's decisions.")
        lines.append("    -> Candidates for removal to reduce model complexity.")

    # Correlations
    if analysis["correlations"]:
        lines.append("")
        lines.append("  CORRELATED PAIRS:")
        for c in analysis["correlations"]:
            tag = " ** REDUNDANT" if c["redundant"] else ""
            lines.append(f"    {c['feature_1']:24s} <-> {c['feature_2']:24s}  r={c['correlation']:.3f}{tag}")

    # Per-action drivers (top 3 features per action)
    if analysis["action_drivers"]:
        lines.append("")
        lines.append("  ACTION DRIVERS (top features per action):")
        for action in sorted(analysis["action_drivers"].keys()):
            drivers = analysis["action_drivers"][action][:3]
            driver_str = ", ".join(f"{d['feature']}({d['count']})" for d in drivers)
            lines.append(f"    {action:24s} <- {driver_str}")

    # Key thresholds for top features
    top_features = [f["name"] for f in imp if f["rank"] in ("HIGH", "MEDIUM")][:5]
    if top_features:
        lines.append("")
        lines.append("  KEY THRESHOLDS (split points PART learned):")
        for feat_name in top_features:
            thresh_list = analysis["thresholds"].get(feat_name, [])
            if thresh_list:
                # Show unique thresholds
                seen = set()
                unique = []
                for t in thresh_list:
                    key = (t["operator"], round(t["threshold"], 2))
                    if key not in seen:
                        seen.add(key)
                        unique.append(t)
                # Show top 3 most common thresholds
                for t in unique[:3]:
                    th = t["threshold"]
                    if th == int(th):
                        th_str = f"{int(th):,}"
                    else:
                        th_str = f"{th:.4g}"
                    lines.append(f"    {feat_name:24s} {t['operator']:>2s} {th_str:>10s}  -> {t['action']}")

    return "\n".join(lines)
