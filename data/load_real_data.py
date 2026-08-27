"""
data/load_real_data.py

Loads real transaction data for the Attest pipeline.

Priority order:
  1. User-provided CSV   — pass --csv path/to/file.csv  (see --help for column mapping)
  2. Kaggle auto-download — ULB Credit Card Fraud dataset (284k real transactions)
                           Downloads automatically via kagglehub (no API key needed).
  3. Synthetic fallback  — runs generate_synthetic.py if offline / Kaggle unavailable.

The Kaggle dataset (mlg-ulb/creditcardfraud):
  - 284,807 real European credit card transactions from September 2013
  - 492 genuine fraud cases (0.17% — real-world rate)
  - Features: Time, V1-V28 (PCA-anonymised for privacy), Amount, Class

Output (same schema as generate_synthetic.py):
  data/transactions.csv
  data/transactions.json
  data/transactions_metadata.json

Usage:
  python data/load_real_data.py                         # Kaggle auto-download
  python data/load_real_data.py --limit 5000            # use 5k rows
  python data/load_real_data.py --csv mydata.csv        # your own CSV
  python data/load_real_data.py --csv mydata.csv \\
      --amount-col spend --fraud-col is_fraud           # custom column names
  python data/load_real_data.py --synthetic             # force synthetic

Column mapping for user CSV (all have defaults):
  --amount-col   column name for transaction amount   (default: Amount)
  --fraud-col    column name for fraud label 0/1      (default: Class)
  --time-col     column name for time/timestamp       (default: Time)
"""

import sys
import json
import uuid
import math
import random
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pandas as pd
from typing import Optional


sys.path.insert(0, str(Path(__file__).parent.parent))

KAGGLE_DATASET   = "mlg-ulb/creditcardfraud"
KAGGLE_FILE      = "creditcard.csv"
OUTPUT_DIR       = Path(__file__).parent
DATA_DIR         = Path(__file__).parent

CHANNELS          = ["upi", "card", "netbanking", "wallet"]
CHANNEL_WEIGHTS   = [32, 42, 18, 8]
MERCHANT_CATS     = ["ecommerce", "travel", "food", "utilities", "gaming", "retail", "insurance"]
MERCHANT_WEIGHTS  = [30, 18, 15, 14, 10, 8, 5]

DECLINE_BY_FRAUD = {
    True:  ["FRAUD_SUSPECTED", "VELOCITY_BREACH", "UNUSUAL_PATTERN"],
    False: ["INSUFFICIENT_FUNDS", "GATEWAY_TIMEOUT", "3DS_FAILED",
            "LOW_BALANCE", "AUTH_DECLINED", "CONNECTION_RESET"],
}

# Map amount brackets to root-cause labels (best-effort; real dataset has no label)
def _label_from_amount_and_fraud(amount: float, is_fraud: bool, hour: int) -> str:
    if is_fraud:
        return "fraud_flag"
    if amount < 20:
        return "insufficient_funds"
    if hour in (0, 1, 2, 3, 23):
        return "gateway_timeout"          # night-time = infra timeouts
    if amount > 500:
        return "auth_3ds_failure"         # high-value = 3DS challenge
    return random.choices(
        ["gateway_timeout", "insufficient_funds", "auth_3ds_failure"],
        weights=[38, 32, 30], k=1
    )[0]


def _time_to_hour(time_seconds: float) -> int:
    """ULB dataset 'Time' is seconds elapsed since first transaction in the dataset."""
    # Assume first transaction was at 8:00 AM (bank opening)
    base_hour = 8
    return int((base_hour + time_seconds / 3600) % 24)


def _map_row(row: pd.Series, amount_col: str, fraud_col: str, time_col: str,
             customer_id: str, customer_amounts: list, i: int) -> dict:
    """Map a row from any input CSV to the Attest transaction schema."""
    amount = float(row.get(amount_col, 100.0))
    is_fraud = bool(int(row.get(fraud_col, 0)))
    time_val = float(row.get(time_col, i * 3600)) if time_col in row.index else i * 3600.0

    hour = _time_to_hour(time_val)
    day_of_week = random.randint(0, 6)
    is_weekend = int(day_of_week >= 5)

    channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
    merchant_cat = random.choices(MERCHANT_CATS, weights=MERCHANT_WEIGHTS, k=1)[0]
    retry_count = random.choices([0, 1, 2, 3, 4], weights=[40, 30, 15, 10, 5], k=1)[0]
    if is_fraud:
        retry_count = random.choices([0, 1], weights=[70, 30], k=1)[0]

    customer_avg = (sum(customer_amounts) / len(customer_amounts)) if customer_amounts else amount
    amount_ratio = round(amount / max(customer_avg, 1.0), 4)

    # Generate a realistic timestamp (last 90 days)
    days_back = random.randint(0, 90)
    ts = datetime.now(timezone.utc) - timedelta(days=days_back, hours=(23 - hour))
    ts = ts.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))

    label = _label_from_amount_and_fraud(amount, is_fraud, hour)
    decline_codes = DECLINE_BY_FRAUD[is_fraud]
    decline_code = random.choice(decline_codes)

    is_recurring = random.random() < (0.35 if label == "insufficient_funds" else 0.18)
    hist_len = random.randint(1, 200)
    time_since = round(random.uniform(0.25, 720), 2)

    return {
        "transaction_id":             str(uuid.uuid4()),
        "customer_id":                customer_id,
        "amount":                     round(amount, 2),
        "channel":                    channel,
        "decline_code":               decline_code,
        "timestamp":                  ts.isoformat(),
        "retry_count_so_far":         retry_count,
        "merchant_category":          merchant_cat,
        "is_recurring":               int(is_recurring),
        "customer_txn_history_len":   hist_len,
        "label":                      label,
        "is_anomaly":                 int(is_fraud),
        "hour_of_day":                hour,
        "day_of_week":                day_of_week,
        "is_weekend":                 is_weekend,
        "amount_log":                 round(math.log1p(amount), 6),
        "time_since_last_failure_hours": time_since,
        "amount_vs_customer_avg_ratio": amount_ratio,
        "customer_risk_tier":         "suspicious" if is_fraud else "standard",
        "data_source":                "kaggle:mlg-ulb/creditcardfraud",
    }


def load_kaggle(limit: Optional[int] = None) -> pd.DataFrame:
    """Auto-download the ULB Credit Card Fraud dataset via kagglehub."""
    try:
        import kagglehub
    except ImportError:
        raise RuntimeError("kagglehub not installed. Run: pip install kagglehub")

    print(f"  Downloading {KAGGLE_DATASET} via kagglehub...")
    path = kagglehub.dataset_download(KAGGLE_DATASET)
    csv_path = Path(path) / KAGGLE_FILE
    if not csv_path.exists():
        raise FileNotFoundError(f"Expected {csv_path} after download")

    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df):,} rows from Kaggle dataset.")
    print(f"  Fraud: {df['Class'].sum()} ({df['Class'].mean()*100:.3f}%)")

    if limit:
        # Stratified sample to preserve fraud rate
        fraud = df[df["Class"] == 1]
        legit = df[df["Class"] == 0]
        n_fraud = min(len(fraud), max(1, int(limit * 0.003)))
        n_legit = limit - n_fraud
        df = pd.concat([
            fraud.sample(n=n_fraud, random_state=42),
            legit.sample(n=n_legit, random_state=42)
        ]).sample(frac=1, random_state=42).reset_index(drop=True)
        print(f"  Sampled {len(df):,} rows (fraud: {df['Class'].sum()}).")

    return df


def load_user_csv(csv_path: str, amount_col: str, fraud_col: str, time_col: str,
                  limit: Optional[int] = None) -> pd.DataFrame:
    """Load a user-provided CSV."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(path)
    print(f"  Loaded {len(df):,} rows from {csv_path}.")
    for col, role in [(amount_col, "amount"), (fraud_col, "fraud label")]:
        if col not in df.columns:
            raise ValueError(
                f"Column '{col}' ({role}) not found in CSV.\n"
                f"  Available columns: {list(df.columns)}\n"
                f"  Use --{role.replace(' ','-')}-col to specify the right column name."
            )
    if limit:
        df = df.head(limit)
    return df


def convert_to_attest_schema(df: pd.DataFrame, amount_col: str = "Amount",
                              fraud_col: str = "Class", time_col: str = "Time") -> list:
    """Convert any input DataFrame to the Attest transaction schema."""
    # Build a small customer pool (1 customer per ~50 transactions)
    n_customers = max(10, len(df) // 50)
    customer_pool = [str(uuid.uuid4()) for _ in range(n_customers)]

    records = []
    customer_amounts: dict = {}

    for i, (_, row) in enumerate(df.iterrows()):
        customer_id = random.choice(customer_pool)
        if customer_id not in customer_amounts:
            customer_amounts[customer_id] = []

        rec = _map_row(row, amount_col, fraud_col, time_col,
                       customer_id, customer_amounts[customer_id], i)
        customer_amounts[customer_id].append(rec["amount"])
        records.append(rec)

    return records


def save_outputs(records: list, source_label: str):
    """Save transactions.csv, transactions.json, transactions_metadata.json."""
    df = pd.DataFrame(records)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_DIR / "transactions.csv", index=False)
    df.to_json(OUTPUT_DIR / "transactions.json", orient="records", indent=2)

    metadata = {
        "total_records":        len(df),
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "data_source":          source_label,
        "class_distribution":   df["label"].value_counts().to_dict(),
        "anomaly_count":        int(df["is_anomaly"].sum()),
        "anomaly_rate_pct":     round(df["is_anomaly"].mean() * 100, 4),
    }
    with open(OUTPUT_DIR / "transactions_metadata.json", "w") as mf:
        json.dump(metadata, mf, indent=2)

    print(f"\n  Saved {len(df):,} records.")
    print(f"  Class distribution:")
    for lbl, cnt in df["label"].value_counts().items():
        print(f"    {lbl:<25} {cnt:>6,}  ({cnt/len(df)*100:.1f}%)")
    print(f"  Anomalies (fraud):   {df['is_anomaly'].sum()} ({df['is_anomaly'].mean()*100:.3f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Load real or user-provided transaction data into the Attest pipeline."
    )
    parser.add_argument("--csv",        help="Path to your own CSV file")
    parser.add_argument("--amount-col", default="Amount", help="Amount column name (default: Amount)")
    parser.add_argument("--fraud-col",  default="Class",  help="Fraud label column 0/1 (default: Class)")
    parser.add_argument("--time-col",   default="Time",   help="Time/timestamp column (default: Time)")
    parser.add_argument("--limit",      type=int,         help="Max number of rows to use")
    parser.add_argument("--synthetic",  action="store_true", help="Force synthetic data generation")
    args = parser.parse_args()

    print("=" * 60)
    print("Attest — Real Data Loader")
    print("=" * 60)

    if args.synthetic:
        print("\n[Mode] Synthetic (forced)")
        subprocess.run([sys.executable, str(DATA_DIR / "generate_synthetic.py")], check=True)
        return

    if args.csv:
        print(f"\n[Mode] User CSV: {args.csv}")
        df = load_user_csv(args.csv, args.amount_col, args.fraud_col, args.time_col, args.limit)
        source = f"user-csv:{Path(args.csv).name}"
    else:
        print(f"\n[Mode] Kaggle: {KAGGLE_DATASET}")
        print("  (284,807 real European credit card transactions, Sep 2013)")
        print("  Auto-downloading via kagglehub (no API key required)...\n")
        try:
            df = load_kaggle(limit=args.limit)
            source = f"kaggle:{KAGGLE_DATASET}"
        except Exception as e:
            print(f"\n  Kaggle download failed: {e}")
            print("  Falling back to synthetic data generator...\n")
            subprocess.run([sys.executable, str(DATA_DIR / "generate_synthetic.py")], check=True)
            return

    print("\n  Mapping to Attest transaction schema...")
    records = convert_to_attest_schema(df, args.amount_col, args.fraud_col, args.time_col)
    save_outputs(records, source)
    print(f"\nDone. Run: python ml/train_classifier.py && python ml/train_anomaly.py")
    print(f"Then:    python demo/run_pipeline.py")


if __name__ == "__main__":
    main()
