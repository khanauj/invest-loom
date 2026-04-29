"""
evaluation.py - Multi-Model Evaluation, Visualization & Interpretability

Supports: Decision Tree, RIPPER (PART-like), CN2
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report, ConfusionMatrixDisplay
from sklearn.tree import DecisionTreeClassifier, plot_tree, export_text

from financial_engine.model_training import pandas_to_orange


# ──────────────────────────────────────────────
#  Prediction helpers
# ──────────────────────────────────────────────

def predict_ripper(ripper_models: dict, raw_test: pd.DataFrame, target_enc) -> np.ndarray:
    """One-vs-rest RIPPER predictions."""
    feature_cols = [c for c in raw_test.columns if c != "action"]
    X_test_raw = raw_test[feature_cols]
    class_list = list(target_enc.classes_)

    scores = pd.DataFrame(index=range(len(X_test_raw)), columns=sorted(ripper_models.keys()))
    for cls, model in ripper_models.items():
        scores[cls] = model.predict(X_test_raw)

    encoded = []
    for i in range(len(X_test_raw)):
        row = scores.iloc[i]
        positives = [c for c in row.index if row[c] == 1]
        label = positives[0] if positives else "HOLD"
        encoded.append(class_list.index(label))
    return np.array(encoded)


def predict_cn2(cn2_model, raw_test: pd.DataFrame, target_enc) -> np.ndarray:
    """CN2 predictions via Orange."""
    orange_test = pandas_to_orange(raw_test, "action")
    pred_indices = [int(cn2_model(row)) for row in orange_test]
    cn2_classes = list(orange_test.domain.class_var.values)
    target_classes = list(target_enc.classes_)
    return np.array([target_classes.index(cn2_classes[idx]) for idx in pred_indices])


# ──────────────────────────────────────────────
#  Metrics
# ──────────────────────────────────────────────

def evaluate_single(model_name: str, y_test, y_pred, class_names, output_dir: str = "output"):
    """Accuracy, classification report, confusion matrix for one model."""
    acc = accuracy_score(y_test, y_pred)
    print(f"  [{model_name}] Test Accuracy: {acc:.4f}")
    print()
    print(classification_report(y_test, y_pred, target_names=class_names, zero_division=0))

    cm = confusion_matrix(y_test, y_pred, labels=list(range(len(class_names))))
    print(pd.DataFrame(cm, index=class_names, columns=class_names))
    print()

    filename = f"{output_dir}/confusion_matrix_{model_name.lower().replace(' ', '_')}.png"
    fig, ax = plt.subplots(figsize=(10, 8))
    ConfusionMatrixDisplay(cm, display_labels=class_names).plot(ax=ax, cmap="Blues")
    ax.set_title(f"Confusion Matrix — {model_name}")
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"  Saved: {filename}")
    return acc


# ──────────────────────────────────────────────
#  Bias check
# ──────────────────────────────────────────────

def check_bias(model_name: str, y_pred, target_enc):
    pred_labels = target_enc.inverse_transform(y_pred)
    dist = pd.Series(pred_labels).value_counts(normalize=True).sort_index()
    print(f"  [{model_name}] Prediction Distribution:")
    for label, pct in dist.items():
        flag = "  ** BIASED **" if pct > 0.40 else ""
        print(f"    {label:24s} : {pct:.2%}{flag}")
    biased = [l for l, p in dist.items() if p > 0.40]
    if biased:
        print(f"  WARNING: {biased} exceed 40% of predictions.")
    else:
        print("  No bias detected.")
    print()


# ──────────────────────────────────────────────
#  Rule extraction
# ──────────────────────────────────────────────

def extract_dt_rules(model, feature_names, target_enc, output_dir="output"):
    class_names = list(target_enc.classes_)
    rules_text = export_text(model, feature_names=feature_names)
    path = f"{output_dir}/decision_rules.txt"
    with open(path, "w") as f:
        f.write("Decision Rules — Decision Tree\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Class mapping: {dict(enumerate(class_names))}\n\n")
        f.write(rules_text)
    print(f"  Decision Tree rules -> {path}")

    img_path = f"{output_dir}/decision_tree.png"
    fig, ax = plt.subplots(figsize=(28, 14))
    plot_tree(model, feature_names=feature_names, class_names=class_names,
              filled=True, rounded=True, fontsize=8, ax=ax)
    ax.set_title("Decision Tree — AI Financial Decision Engine", fontsize=14)
    plt.tight_layout()
    plt.savefig(img_path, dpi=150)
    plt.close()
    print(f"  Decision Tree plot  -> {img_path}")


def extract_ripper_rules(ripper_models, output_dir="output"):
    path = f"{output_dir}/ripper_rules.txt"
    lines = []
    for cls in sorted(ripper_models.keys()):
        model = ripper_models[cls]
        lines.append(f"\n[{cls}]")
        if len(model.ruleset_) == 0:
            lines.append("  (no specific rules — default negative)")
        else:
            for rule in model.ruleset_:
                lines.append(f"  {rule}")
    with open(path, "w") as f:
        f.write("Decision Rules — RIPPER (PART-like, One-vs-Rest)\n")
        f.write("=" * 50 + "\n")
        f.write("\n".join(lines))
    print(f"  RIPPER rules        -> {path}")


def extract_cn2_rules(cn2_model, output_dir="output"):
    path = f"{output_dir}/cn2_rules.txt"
    lines = [str(rule) for rule in cn2_model.rule_list]
    with open(path, "w") as f:
        f.write("Decision Rules — CN2 Rule Induction\n")
        f.write("=" * 50 + "\n\n")
        f.write("\n".join(lines))
    print(f"  CN2 rules           -> {path}")


# ──────────────────────────────────────────────
#  Comparison
# ──────────────────────────────────────────────

def compare_models(results: dict):
    print("\n" + "=" * 50)
    print("  MODEL COMPARISON")
    print("=" * 50)
    print(f"  {'Model':<25s} {'Accuracy':>10s}")
    print("  " + "-" * 37)
    for name, acc in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"  {name:<25s} {acc:>10.4f}")
    best = max(results, key=results.get)
    print(f"\n  Best: {best} ({results[best]:.4f})")
    print("=" * 50 + "\n")


# ──────────────────────────────────────────────
#  Full evaluation pipeline
# ──────────────────────────────────────────────

def run_evaluation(models, data, output_dir="output"):
    """Evaluate all models, extract rules, compare."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    class_names = list(data["target_enc"].classes_)
    results = {}

    # Decision Tree
    print("\n" + "=" * 50)
    print("  DECISION TREE EVALUATION")
    print("=" * 50)
    y_pred_dt = models["Decision Tree"].predict(data["X_test"])
    results["Decision Tree"] = evaluate_single("Decision Tree", data["y_test"], y_pred_dt, class_names, output_dir)
    check_bias("Decision Tree", y_pred_dt, data["target_enc"])
    extract_dt_rules(models["Decision Tree"], data["feature_names"], data["target_enc"], output_dir)

    # RIPPER
    print("\n" + "=" * 50)
    print("  RIPPER EVALUATION")
    print("=" * 50)
    y_pred_rip = predict_ripper(models["RIPPER"], data["raw_test"], data["target_enc"])
    results["RIPPER"] = evaluate_single("RIPPER", data["y_test"], y_pred_rip, class_names, output_dir)
    check_bias("RIPPER", y_pred_rip, data["target_enc"])
    extract_ripper_rules(models["RIPPER"], output_dir)

    # CN2
    print("\n" + "=" * 50)
    print("  CN2 EVALUATION")
    print("=" * 50)
    y_pred_cn2 = predict_cn2(models["CN2"], data["raw_test"], data["target_enc"])
    results["CN2"] = evaluate_single("CN2", data["y_test"], y_pred_cn2, class_names, output_dir)
    check_bias("CN2", y_pred_cn2, data["target_enc"])
    extract_cn2_rules(models["CN2"], output_dir)

    compare_models(results)
    return results
