#!/usr/bin/env python3
"""
startup.py — Render startup script

Trains ML models if they are not present (e.g. first deploy).
Run before starting the uvicorn server.

Usage (Render Start Command):
    python startup.py && uvicorn server:app --host 0.0.0.0 --port $PORT
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"


def need_training() -> bool:
    required = [
        MODELS_DIR / "classifier.pkl",
        MODELS_DIR / "anomaly_detector.pkl",
        MODELS_DIR / "shap_explainer.pkl",
    ]
    missing = [f for f in required if not f.exists()]
    if missing:
        print(f"[startup] Missing model files: {[f.name for f in missing]}")
        return True
    return False


def run(cmd, label):
    print(f"\n[startup] ▶ {label}")
    result = subprocess.run(
        [sys.executable] + cmd,
        capture_output=False,
        text=True,
    )
    if result.returncode != 0:
        print(f"[startup] ✗ {label} failed (exit {result.returncode})")
        sys.exit(result.returncode)
    print(f"[startup] ✓ {label} complete")


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if not need_training():
        print("[startup] ✓ All models present — skipping training")
        return

    print("[startup] ═══════════════════════════════════════════")
    print("[startup]  First deploy — training ML models...")
    print("[startup] ═══════════════════════════════════════════")

    # 1. Generate synthetic training data if not present
    if not (DATA_DIR / "transactions.csv").exists():
        run(["data/generate_synthetic.py"], "Generating training data (10k records)")
    else:
        print("[startup] ✓ Training data already present")

    # 2. Train XGBoost classifier
    run(["ml/train_classifier.py"], "Training XGBoost classifier")

    # 3. Train Isolation Forest anomaly detector
    run(["ml/train_anomaly.py"], "Training Isolation Forest anomaly detector")

    print("\n[startup] ✅ All models trained and ready!")


if __name__ == "__main__":
    main()
