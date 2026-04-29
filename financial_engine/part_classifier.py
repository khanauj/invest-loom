"""
part_classifier.py - Native Python Implementation of PART Algorithm

PART (Partial Decision Trees) — Frank & Witten, 1998
Original: Weka (Java). This is a pure Python reimplementation.

How PART works:
  1. Build a decision tree on the current dataset
  2. Find the leaf with the highest coverage (most examples)
  3. Extract the path from root to that leaf as a rule
  4. Remove all examples covered by this rule
  5. Repeat until all examples are covered

The key insight: instead of building a FULL tree and then extracting
ALL rules (like C4.5), PART builds PARTIAL trees — it only takes the
BEST rule from each tree, then rebuilds. This produces simpler,
more accurate rulesets.

Usage:
    model = PARTClassifier(max_depth=6, min_samples_leaf=5)
    model.fit(X_train, y_train, feature_names=['salary', 'savings', ...])
    predictions = model.predict(X_test)
    model.print_rules()
"""

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text


class PARTRule:
    """A single IF-THEN rule extracted from a partial decision tree."""

    def __init__(self, conditions, prediction, coverage, accuracy, class_name=None):
        """
        Args:
            conditions: list of (feature_index, operator, threshold, feature_name)
            prediction: predicted class (encoded)
            coverage: number of training examples this rule covers
            accuracy: accuracy on covered examples
            class_name: human-readable class name
        """
        self.conditions = conditions
        self.prediction = prediction
        self.coverage = coverage
        self.accuracy = accuracy
        self.class_name = class_name

    def matches(self, X_row):
        """Check if a single row matches all conditions."""
        for feat_idx, op, threshold, _ in self.conditions:
            val = X_row[feat_idx]
            if op == "<=" and not (val <= threshold):
                return False
            if op == ">" and not (val > threshold):
                return False
        return True

    def __str__(self):
        if not self.conditions:
            return f"DEFAULT → {self.class_name} (coverage: {self.coverage}, acc: {self.accuracy:.1%})"
        parts = []
        for _, op, threshold, feat_name in self.conditions:
            if isinstance(threshold, float) and threshold == int(threshold):
                parts.append(f"{feat_name} {op} {int(threshold)}")
            else:
                parts.append(f"{feat_name} {op} {threshold:.4g}")
        return (f"IF {' AND '.join(parts)} → {self.class_name} "
                f"(coverage: {self.coverage}, acc: {self.accuracy:.1%})")


class PARTClassifier:
    """
    PART (Partial Decision Trees) classifier.

    Builds partial decision trees iteratively, extracts one rule per tree,
    removes covered examples, repeats until dataset is empty.
    """

    def __init__(self, max_depth=6, min_samples_leaf=5, min_coverage=3,
                 random_state=42):
        """
        Args:
            max_depth: max depth for each partial decision tree
            min_samples_leaf: minimum samples per leaf in partial trees
            min_coverage: stop extracting rules when remaining examples < this
            random_state: random seed for reproducibility
        """
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.min_coverage = min_coverage
        self.random_state = random_state
        self.rules = []
        self.default_class = None
        self.feature_names = None
        self.class_names = None

    def fit(self, X, y, feature_names=None, class_names=None):
        """
        Train PART by iteratively building partial decision trees.

        Args:
            X: feature matrix (numpy array or DataFrame)
            y: target labels (encoded as integers)
            feature_names: list of feature names
            class_names: list of class names (indexed by y values)
        """
        if isinstance(X, pd.DataFrame):
            if feature_names is None:
                feature_names = list(X.columns)
            X = X.values.copy()
        else:
            X = np.array(X, dtype=float).copy()

        y = np.array(y, dtype=int).copy()
        self.feature_names = feature_names or [f"f{i}" for i in range(X.shape[1])]
        self.class_names = class_names
        self.rules = []

        # Track which examples are still uncovered
        remaining_mask = np.ones(len(X), dtype=bool)

        iteration = 0
        max_iterations = 200  # safety limit

        while remaining_mask.sum() >= self.min_coverage and iteration < max_iterations:
            iteration += 1

            X_remaining = X[remaining_mask]
            y_remaining = y[remaining_mask]

            # Check if all remaining examples are same class
            if len(np.unique(y_remaining)) == 1:
                cls = y_remaining[0]
                cls_name = self.class_names[cls] if self.class_names else str(cls)
                self.rules.append(PARTRule(
                    conditions=[],
                    prediction=cls,
                    coverage=len(y_remaining),
                    accuracy=1.0,
                    class_name=cls_name,
                ))
                remaining_mask[:] = False
                break

            # Build a partial decision tree
            tree = DecisionTreeClassifier(
                max_depth=self.max_depth,
                min_samples_leaf=self.min_samples_leaf,
                random_state=self.random_state,
            )
            tree.fit(X_remaining, y_remaining)

            # Extract the best rule (highest coverage leaf)
            rule = self._extract_best_rule(tree, X_remaining, y_remaining)

            if rule is None or rule.coverage < self.min_coverage:
                break

            self.rules.append(rule)

            # Remove covered examples from the remaining set
            original_indices = np.where(remaining_mask)[0]
            for idx in original_indices:
                if rule.matches(X[idx]):
                    remaining_mask[idx] = False

        # Default rule for anything not covered
        if remaining_mask.sum() > 0:
            y_remaining = y[remaining_mask]
            if len(y_remaining) > 0:
                default_cls = np.bincount(y_remaining).argmax()
            else:
                default_cls = np.bincount(y).argmax()
        else:
            default_cls = np.bincount(y).argmax()

        cls_name = self.class_names[default_cls] if self.class_names else str(default_cls)
        self.default_class = default_cls
        self.rules.append(PARTRule(
            conditions=[],
            prediction=default_cls,
            coverage=remaining_mask.sum(),
            accuracy=1.0,
            class_name=cls_name,
        ))

        return self

    def _extract_best_rule(self, tree, X, y):
        """Extract the best rule from a fitted decision tree."""
        tree_model = tree.tree_

        # Find all leaves
        leaves = []
        self._find_leaves(tree_model, 0, [], X, y, leaves)

        if not leaves:
            return None

        # Pick the leaf with highest coverage × accuracy
        best = max(leaves, key=lambda l: l["coverage"] * l["accuracy"])

        conditions = []
        for feat_idx, op, threshold in best["path"]:
            feat_name = self.feature_names[feat_idx]
            conditions.append((feat_idx, op, threshold, feat_name))

        cls = best["prediction"]
        cls_name = self.class_names[cls] if self.class_names else str(cls)

        return PARTRule(
            conditions=conditions,
            prediction=cls,
            coverage=best["coverage"],
            accuracy=best["accuracy"],
            class_name=cls_name,
        )

    def _find_leaves(self, tree, node_id, path, X, y, leaves):
        """Recursively find all leaves in the tree with their paths."""
        # Check if leaf
        if tree.children_left[node_id] == tree.children_right[node_id]:
            # This is a leaf — evaluate it
            mask = np.ones(len(X), dtype=bool)
            for feat_idx, op, threshold in path:
                if op == "<=":
                    mask &= X[:, feat_idx] <= threshold
                else:
                    mask &= X[:, feat_idx] > threshold

            coverage = mask.sum()
            if coverage > 0:
                y_covered = y[mask]
                prediction = np.bincount(y_covered).argmax()
                accuracy = (y_covered == prediction).mean()
                leaves.append({
                    "path": list(path),
                    "prediction": prediction,
                    "coverage": coverage,
                    "accuracy": accuracy,
                })
            return

        # Internal node — branch left and right
        feature = tree.feature[node_id]
        threshold = round(float(tree.threshold[node_id]), 4)

        # Left branch: feature <= threshold
        left_path = path + [(feature, "<=", threshold)]
        self._find_leaves(tree, tree.children_left[node_id], left_path, X, y, leaves)

        # Right branch: feature > threshold
        right_path = path + [(feature, ">", threshold)]
        self._find_leaves(tree, tree.children_right[node_id], right_path, X, y, leaves)

    def predict(self, X):
        """Predict class labels for X."""
        if isinstance(X, pd.DataFrame):
            X = X.values

        X = np.array(X, dtype=float)
        predictions = np.full(len(X), self.default_class, dtype=int)

        for i in range(len(X)):
            for rule in self.rules:
                if rule.matches(X[i]):
                    predictions[i] = rule.prediction
                    break

        return predictions

    def predict_single(self, X_row):
        """Predict a single row. Returns (prediction, rule_index, rule)."""
        if isinstance(X_row, pd.DataFrame):
            X_row = X_row.values[0]
        X_row = np.array(X_row, dtype=float)

        for i, rule in enumerate(self.rules):
            if rule.matches(X_row):
                return rule.prediction, i, rule

        return self.default_class, len(self.rules) - 1, self.rules[-1]

    def print_rules(self):
        """Print all extracted rules."""
        print(f"PART Rules ({len(self.rules)} rules):")
        print("=" * 60)
        for i, rule in enumerate(self.rules, 1):
            print(f"  Rule {i:3d}: {rule}")
        print("=" * 60)

    def get_rules_text(self):
        """Return rules as a string."""
        lines = [f"PART Rules ({len(self.rules)} rules)", "=" * 60]
        for i, rule in enumerate(self.rules, 1):
            lines.append(f"Rule {i:3d}: {rule}")
        return "\n".join(lines)

    def get_rule_count(self):
        """Return number of extracted rules."""
        return len(self.rules)
