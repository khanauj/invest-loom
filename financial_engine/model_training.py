"""
model_training.py - PART Model Training

Model:
  PART — partial decision tree rule extractor, native Python
"""

import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from financial_engine.part_classifier import PARTClassifier


SEED = 42
CATEGORICAL_COLS = ["risk_level", "investment_experience", "sip_active"]
TARGET_COL = "action"


# ──────────────────────────────────────────────
#  Data loading & encoding
# ──────────────────────────────────────────────

def load_and_encode(csv_path: str):
    """
    Load dataset and encode categorical features to numeric values.
    Returns dict with all train/test splits and metadata.
    """
    df = pd.read_csv(csv_path)

    # Ensure sip_active is string for encoding
    df["sip_active"] = df["sip_active"].astype(str)

    encoders = {}
    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le

    target_enc = LabelEncoder()
    df[TARGET_COL] = target_enc.fit_transform(df[TARGET_COL])

    feature_cols = [c for c in df.columns if c != TARGET_COL]
    X = df[feature_cols]
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )

    print(f"Training set : {len(X_train)} samples")
    print(f"Test set     : {len(X_test)} samples")
    print(f"Features     : {list(feature_cols)}")
    print(f"Classes      : {list(target_enc.classes_)}")
    print()

    return {
        "X_train": X_train, "X_test": X_test,
        "y_train": y_train, "y_test": y_test,
        "encoders": encoders, "feature_names": feature_cols,
        "target_enc": target_enc,
    }


# ──────────────────────────────────────────────
#  PART (Partial Decision Trees)
# ──────────────────────────────────────────────

def train_part(X_train, y_train, feature_names, target_enc):
    """Train a PART classifier using native Python implementation."""
    class_names = list(target_enc.classes_)
    part_model = PARTClassifier(
        max_depth=6,
        min_samples_leaf=5,
        min_coverage=3,
        random_state=SEED,
    )
    part_model.fit(X_train, y_train,
                   feature_names=list(feature_names),
                   class_names=class_names)
    print(f"  PART trained -- {part_model.get_rule_count()} rules extracted")
    return part_model


# ──────────────────────────────────────────────
#  Model persistence
# ──────────────────────────────────────────────

def save_models(models: dict, data_bundle: dict, output_dir: str = "models"):
    """Save PART model and metadata to disk."""
    os.makedirs(output_dir, exist_ok=True)

    joblib.dump(models["PART"], os.path.join(output_dir, "part_model.joblib"))
    joblib.dump(data_bundle["target_enc"], os.path.join(output_dir, "target_encoder.joblib"))
    joblib.dump(data_bundle["encoders"], os.path.join(output_dir, "feature_encoders.joblib"))
    joblib.dump(data_bundle["feature_names"], os.path.join(output_dir, "feature_names.joblib"))
    joblib.dump(data_bundle["X_train"], os.path.join(output_dir, "X_train.joblib"))

    print(f"\nModel saved to {output_dir}/")


def load_models(model_dir: str = "models") -> tuple:
    """Load PART model and metadata from disk."""
    target_enc = joblib.load(os.path.join(model_dir, "target_encoder.joblib"))
    encoders = joblib.load(os.path.join(model_dir, "feature_encoders.joblib"))
    feature_names = joblib.load(os.path.join(model_dir, "feature_names.joblib"))
    part_model = joblib.load(os.path.join(model_dir, "part_model.joblib"))
    X_train = joblib.load(os.path.join(model_dir, "X_train.joblib"))

    models = {"PART": part_model}
    data_bundle = {
        "target_enc": target_enc,
        "encoders": encoders,
        "feature_names": feature_names,
        "X_train": X_train,
    }
    return models, data_bundle


# ──────────────────────────────────────────────
#  Full training pipeline
# ──────────────────────────────────────────────

def run_training(csv_path: str = "financial_dataset.csv", model_dir: str = "models"):
    """Train PART model, save to disk."""
    data = load_and_encode(csv_path)

    print("[1/1] PART (Partial Decision Trees)")
    print("-" * 40)
    part_model = train_part(data["X_train"], data["y_train"],
                            data["feature_names"], data["target_enc"])
    print()

    models = {"PART": part_model}

    save_models(models, data, model_dir)
    return models, data
