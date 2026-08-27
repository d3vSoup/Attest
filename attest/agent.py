"""
attest/agent.py

The demo decision agent. Given a failed transaction dict, uses the
trained XGBoost classifier to predict root cause, then selects a recovery
action within policy bounds. Decorated with @audited_action so every
call is automatically hashed, stored, and Merkle-batched.
"""

import joblib
import numpy as np
import pandas as pd
import math
from pathlib import Path
from .wrapper import audited_action

CLASSIFIER_PATH = Path(__file__).parent.parent / "models" / "classifier.pkl"
SHAP_PATH = Path(__file__).parent.parent / "models" / "shap_explainer.pkl"
POLICY_PATH = Path(__file__).parent.parent / "policy.yaml"

CLASS_NAMES = ["insufficient_funds", "auth_3ds_failure", "gateway_timeout", "fraud_flag"]

# Root cause → default action and discount
ACTION_POLICY = {
    "insufficient_funds": {"action": "alt_payment_nudge", "discount_pct": 0.0},
    "auth_3ds_failure":   {"action": "retry",             "discount_pct": 0.0},
    "gateway_timeout":    {"action": "retry",             "discount_pct": 0.0},
    "fraud_flag":         {"action": "escalate",          "discount_pct": 0.0},
}

# If already retried >= threshold times, switch to discount
RETRY_DISCOUNT_THRESHOLD = 2
DISCOUNT_PCT = 5.0  # within the 10% policy max

DECLINE_MAP = {
    "INSUFFICIENT_FUNDS": 0, "LOW_BALANCE": 1, "CREDIT_LIMIT_EXCEEDED": 2,
    "3DS_FAILED": 3, "OTP_TIMEOUT": 4, "AUTH_DECLINED": 5,
    "GATEWAY_TIMEOUT": 6, "CONNECTION_RESET": 7, "UPSTREAM_ERROR": 8,
    "FRAUD_SUSPECTED": 9, "VELOCITY_BREACH": 10, "UNUSUAL_PATTERN": 11,
}

_classifier = None
_explainer_data = None

def _load_classifier():
    global _classifier
    if _classifier is None and CLASSIFIER_PATH.exists():
        _classifier = joblib.load(str(CLASSIFIER_PATH))
    return _classifier

def _load_explainer():
    global _explainer_data
    if _explainer_data is None and SHAP_PATH.exists():
        _explainer_data = joblib.load(str(SHAP_PATH))
    return _explainer_data


def _build_feature_row(transaction: dict) -> pd.DataFrame:
    """Build a 1-row DataFrame matching the classifier's expected features."""
    amount = float(transaction.get("amount", 1000))
    return pd.DataFrame([{
        "amount_log":                    math.log1p(amount),
        "hour_of_day":                   int(transaction.get("hour_of_day", 12)),
        "day_of_week":                   int(transaction.get("day_of_week", 0)),
        "is_weekend":                    int(transaction.get("is_weekend", False)),
        "channel":                       transaction.get("channel", "upi"),
        "retry_count_so_far":            int(transaction.get("retry_count_so_far", 0)),
        "customer_txn_history_len":      int(transaction.get("customer_txn_history_len", 10)),
        "decline_code_enc":              DECLINE_MAP.get(
                                             transaction.get("decline_code", "INSUFFICIENT_FUNDS"), 0
                                         ),
        "merchant_category":             transaction.get("merchant_category", "ecommerce"),
        "amount_vs_customer_avg_ratio":  float(transaction.get("amount_vs_customer_avg_ratio", 1.0)),
        "time_since_last_failure_hours": float(transaction.get("time_since_last_failure_hours", 24.0)),
        "is_recurring":                  int(transaction.get("is_recurring", False)),
    }])


@audited_action(policy_path=POLICY_PATH)
def decide_recovery_action(transaction: dict) -> dict:
    """
    Given a failed transaction, predict root cause and select a recovery action.
    The @audited_action decorator handles all hashing, storage, and anchoring.
    """
    clf = _load_classifier()

    if clf is None:
        # Fallback: rules-based if model not trained yet
        return {"action": "escalate", "discount_pct": 0.0, "confidence": 0.50,
                "predicted_class": "unknown"}

    X = _build_feature_row(transaction)
    proba = clf.predict_proba(X)[0]
    predicted_class_idx = int(np.argmax(proba))
    confidence = float(proba[predicted_class_idx])
    predicted_class = CLASS_NAMES[predicted_class_idx]

    base = ACTION_POLICY[predicted_class].copy()
    action = base["action"]
    discount_pct = base["discount_pct"]

    # Escalate to discount if already retried too many times
    if action == "retry" and transaction.get("retry_count_so_far", 0) >= RETRY_DISCOUNT_THRESHOLD:
        action = "discount"
        discount_pct = DISCOUNT_PCT

    # --- SHAP Explainability ---
    explainer_data = _load_explainer()
    explainability = {}
    if explainer_data is not None:
        # Preprocessor step transforms X
        preprocessor = clf.named_steps["pre"]
        xgb_model = clf.named_steps["clf"]
        
        # Transform X to the feature space XGBoost sees
        X_trans = preprocessor.transform(X)
        
        # Get SHAP values
        explainer = explainer_data["explainer"]
        feature_names = explainer_data["feature_names"]
        
        # explainer.shap_values returns list of arrays for multi-class
        shap_vals = explainer.shap_values(X_trans)
        
        # Get the SHAP values for the predicted class
        if isinstance(shap_vals, list):
            class_shap = shap_vals[predicted_class_idx][0]
        else:
            # Depending on SHAP version, it might be a 3D array
            if len(shap_vals.shape) == 3:
                class_shap = shap_vals[0, :, predicted_class_idx]
            else:
                class_shap = shap_vals[0]
                
        # Sort features by absolute impact
        impacts = []
        for i, val in enumerate(class_shap):
            if i < len(feature_names) and abs(val) > 0.001:
                impacts.append({
                    "feature": feature_names[i],
                    "impact": round(float(val), 4)
                })
        
        impacts.sort(key=lambda x: abs(x["impact"]), reverse=True)
        # Keep top 3 features
        explainability = {
            "top_factors": impacts[:3]
        }

    return {
        "action": action,
        "discount_pct": discount_pct,
        "confidence": confidence,
        "predicted_class": predicted_class,
        "explainability": explainability,
    }
