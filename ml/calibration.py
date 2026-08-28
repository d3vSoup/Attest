"""
ml/calibration.py — Probability Calibration Engine

Checks whether the XGBoost classifier's predicted fraud probabilities are
well-calibrated against the empirically observed fraud rates in the Kaggle data.

A well-calibrated model: when it says "70% fraud probability", exactly 70% of those
transactions are actually fraud. Shows the reliability diagram (calibration curve).

Uses sklearn's calibration_curve with Platt scaling.
"""

import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent


def _load_model():
    """Load the trained XGBoost sklearn Pipeline via joblib."""
    import joblib
    model_path = ROOT / "models" / "classifier.pkl"
    if not model_path.exists():
        return None
    return joblib.load(str(model_path))


def _load_features(csv_path: Optional[Path] = None) -> tuple:
    """
    Load features and labels from the transactions CSV.
    Returns (X, y) where y is binary (1=fraud, 0=normal).
    """
    path = csv_path or ROOT / "data" / "transactions.csv"
    df = pd.read_csv(path)

    # Binary label: fraud_flag = 1, everything else = 0
    y = (df["label"] == "fraud_flag").astype(int)

    # Same feature set as train_classifier.py
    numeric_feats = [
        "amount", "amount_log", "retry_count_so_far",
        "customer_txn_history_len", "hour_of_day", "day_of_week",
        "is_weekend", "is_recurring", "amount_vs_customer_avg_ratio",
        "time_since_last_failure_hours",
    ]
    cat_feats = ["channel", "merchant_category", "customer_risk_tier"]

    # Use available features only
    feats = []
    for f in numeric_feats:
        if f in df.columns:
            feats.append(f)

    X = df[feats].fillna(0)

    # One-hot encode categoricals if present
    for cf in cat_feats:
        if cf in df.columns:
            dummies = pd.get_dummies(df[cf], prefix=cf)
            X = pd.concat([X, dummies], axis=1)

    return X, y


def run_calibration(
    csv_path: Optional[Path] = None,
    n_bins: int = 10,
) -> dict:
    """
    Compute calibration curve for the XGBoost classifier.

    Returns:
      - fraction_of_positives: observed fraud rate in each probability bin
      - mean_predicted_value: mean predicted probability in each bin
      - brier_score: overall calibration score (lower is better)
      - expected_calibration_error (ECE): weighted calibration error
      - model_auc: approximate AUC from calibration data
      - histogram: {bins, counts} of predicted probabilities
      - channel_calibration: per-channel calibration data
      - summary: human-readable assessment
    """
    from sklearn.calibration import calibration_curve
    from sklearn.metrics import brier_score_loss, roc_auc_score

    model = _load_model()
    if model is None:
        return {"error": "Model not found. Run ml/train_classifier.py first."}

    X, y = _load_features(csv_path)

    # Load raw dataframe for pipeline (handles preprocessing internally)
    df_raw = pd.read_csv(csv_path or ROOT / "data" / "transactions.csv")

    # Get predicted probabilities — pipeline handles preprocessing
    try:
        proba = model.predict_proba(df_raw)
        # Classes are integers [0,1,2,3] mapped alphabetically:
        # 0=auth_3ds_failure, 1=fraud_flag, 2=gateway_timeout, 3=insufficient_funds
        fraud_idx = 1  # fraud_flag is always index 1 (alphabetical order)
        y_prob = proba[:, fraud_idx]
    except Exception as e:
        return {"error": f"Prediction failed: {str(e)}"}


    # Calibration curve
    fraction_pos, mean_pred = calibration_curve(y, y_prob, n_bins=n_bins, strategy="uniform")

    # Brier score (lower = better, 0 = perfect)
    brier = float(brier_score_loss(y, y_prob))

    # Expected Calibration Error
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(y)
    for i in range(n_bins):
        mask = (y_prob >= bin_boundaries[i]) & (y_prob < bin_boundaries[i + 1])
        if mask.sum() > 0:
            acc = float(y[mask].mean())
            conf = float(y_prob[mask].mean())
            ece += (mask.sum() / n) * abs(acc - conf)

    # AUC
    try:
        auc = float(roc_auc_score(y, y_prob))
    except Exception:
        auc = 0.0

    # Probability histogram
    hist_counts, hist_bins = np.histogram(y_prob, bins=20)

    # Per-channel calibration
    df = pd.read_csv(csv_path or ROOT / "data" / "transactions.csv")
    channel_cal = {}
    if "channel" in df.columns and len(y_prob) == len(df):
        df = df.copy()
        df["y_prob"] = y_prob
        df["y_true"] = (df["label"] == "fraud_flag").astype(int)
        for ch in df["channel"].unique():
            ch_df = df[df["channel"] == ch]
            if len(ch_df) < 5:
                continue
            ch_y = ch_df["y_true"].values
            ch_prob = ch_df["y_prob"].values
            ch_fraud_rate = float(ch_y.mean())
            ch_pred_rate = float(ch_prob.mean())
            ch_brier = float(brier_score_loss(ch_y, ch_prob))
            channel_cal[ch] = {
                "actual_fraud_rate": round(ch_fraud_rate * 100, 2),
                "predicted_fraud_rate": round(ch_pred_rate * 100, 2),
                "brier_score": round(ch_brier, 4),
                "n_transactions": int(len(ch_df)),
                "calibration_gap": round(abs(ch_fraud_rate - ch_pred_rate) * 100, 2),
            }

    # Human-readable summary
    if brier < 0.02:
        assessment = "EXCELLENT — Model probabilities are highly accurate"
    elif brier < 0.05:
        assessment = "GOOD — Minor calibration drift, within acceptable range"
    elif brier < 0.10:
        assessment = "FAIR — Model overconfident in some probability ranges"
    else:
        assessment = "POOR — Significant calibration error, recalibration recommended"

    return {
        "fraction_of_positives": [round(float(v), 4) for v in fraction_pos],
        "mean_predicted_value": [round(float(v), 4) for v in mean_pred],
        "brier_score": round(brier, 4),
        "ece": round(ece, 4),
        "model_auc": round(auc, 4),
        "histogram": {
            "bins": [round(float(b), 3) for b in hist_bins[:-1]],
            "counts": [int(c) for c in hist_counts],
        },
        "channel_calibration": channel_cal,
        "n_samples": int(len(y)),
        "n_fraud": int(y.sum()),
        "fraud_base_rate_pct": round(float(y.mean()) * 100, 3),
        "assessment": assessment,
        "n_bins": n_bins,
    }


if __name__ == "__main__":
    import json
    result = run_calibration()
    if "error" in result:
        print("Error:", result["error"])
    else:
        print(f"Brier Score: {result['brier_score']:.4f}")
        print(f"ECE: {result['ece']:.4f}")
        print(f"AUC: {result['model_auc']:.4f}")
        print(f"Assessment: {result['assessment']}")
        print(f"Base fraud rate: {result['fraud_base_rate_pct']:.3f}%")
        print("\nPer-channel calibration:")
        for ch, data in result["channel_calibration"].items():
            print(f"  {ch:12s}: actual={data['actual_fraud_rate']:.2f}%  predicted={data['predicted_fraud_rate']:.2f}%  gap={data['calibration_gap']:.2f}%")
