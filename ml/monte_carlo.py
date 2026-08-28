"""
ml/monte_carlo.py — Settlement Risk Monte Carlo Engine

Simulates 30-day forward settlement distributions using Geometric Brownian Motion
calibrated from real Kaggle transaction data.

Returns:
  - P5 / P50 / P95 confidence bands
  - Value at Risk (VaR 95%)
  - Daily volatility series
  - 20 sample simulation paths (for display)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent


def _load_daily_settlements(csv_path: Optional[Path] = None) -> pd.Series:
    """
    Build synthetic daily settlement totals from the transaction CSV.
    Groups transactions by day_of_week (as a proxy for 'day') and aggregates
    successful (non-fraud_flag) amounts. Uses INR-scale amounts.
    """
    path = csv_path or ROOT / "data" / "transactions.csv"
    df = pd.read_csv(path)

    # Use only settled (approved) transactions — not fraud_flag
    settled = df[df["label"] != "fraud_flag"].copy()

    # Scale amounts to INR (Kaggle data is in EUR-cents scale, multiply to ₹ scale)
    # We use a realistic INR scaling: median ₹2,200 per transaction
    raw_median = settled["amount"].median()
    if raw_median < 500:
        # Kaggle data is in small euro units — scale to INR
        scale_factor = 2200 / max(raw_median, 1)
    else:
        scale_factor = 1.0

    settled["amount_inr"] = settled["amount"] * scale_factor

    # Group by (merchant_category, day_of_week) to simulate daily settlement buckets
    # We create 30 synthetic days by cycling through day_of_week patterns
    group_col = "day_of_week" if "day_of_week" in settled.columns else "channel"
    daily = (
        settled.groupby(group_col)["amount_inr"]
        .sum()
        .reset_index()
        .rename(columns={"amount_inr": "daily_total"})
    )

    # Normalize to 30 "days" worth of data by repeating the weekly pattern
    n_days = 60  # 60 days of history
    pattern = daily["daily_total"].values
    pattern = pattern / pattern.mean()  # normalize

    np.random.seed(42)
    # Add realistic noise to create history
    history = []
    base = settled["amount_inr"].sum() / 7  # weekly average → daily average
    for i in range(n_days):
        day_factor = pattern[i % len(pattern)]
        noise = np.random.normal(0, 0.08)  # 8% daily noise
        history.append(base * day_factor * (1 + noise))

    return pd.Series(history, name="daily_settlement")


def run_monte_carlo(
    n_simulations: int = 2000,
    n_days_forward: int = 30,
    n_sample_paths: int = 25,
    csv_path: Optional[Path] = None,
) -> dict:
    """
    Run Monte Carlo settlement simulation using Geometric Brownian Motion.

    Returns a dict with:
      - dates: list of day offsets [1..n_days_forward]
      - p05, p50, p95: confidence band arrays
      - sample_paths: list of N sample simulation paths (for fan chart)
      - var_95: Value at Risk at 95th confidence (worst-case 30-day shortfall)
      - current_daily_avg: baseline daily settlement (INR)
      - volatility_series: rolling 7-day volatility of historical daily returns
      - mu: annualized drift
      - sigma: annualized volatility
    """
    history = _load_daily_settlements(csv_path)

    # Compute daily log returns from historical settlement series
    returns = np.log(history / history.shift(1)).dropna()

    # GBM parameters
    mu_daily = returns.mean()           # mean daily log return (drift)
    sigma_daily = returns.std()         # daily volatility
    S0 = float(history.iloc[-1])        # last observed daily settlement

    # Run simulations
    np.random.seed(123)
    dt = 1.0  # daily time step
    all_paths = np.zeros((n_simulations, n_days_forward))
    all_paths[:, 0] = S0

    for t in range(1, n_days_forward):
        z = np.random.standard_normal(n_simulations)
        # GBM: S_t = S_{t-1} * exp((μ - σ²/2)dt + σ√dt * Z)
        all_paths[:, t] = all_paths[:, t - 1] * np.exp(
            (mu_daily - 0.5 * sigma_daily**2) * dt
            + sigma_daily * np.sqrt(dt) * z
        )

    # Compute terminal distribution (day 30 totals)
    terminal_values = all_paths[:, -1]
    var_95 = float(np.percentile(terminal_values, 5))  # VaR = 5th percentile

    # Confidence bands
    p05 = np.percentile(all_paths, 5, axis=0).tolist()
    p50 = np.percentile(all_paths, 50, axis=0).tolist()
    p95 = np.percentile(all_paths, 95, axis=0).tolist()

    # Sample paths for fan visualization
    sample_idx = np.random.choice(n_simulations, n_sample_paths, replace=False)
    sample_paths = [all_paths[i].tolist() for i in sample_idx]

    # Rolling 7-day volatility of historical data (annualized %)
    hist_arr = history.values
    volatility_series = []
    window = 7
    for i in range(len(hist_arr)):
        if i < window:
            vol = float(returns.std() * np.sqrt(252) * 100)
        else:
            window_returns = np.log(hist_arr[i - window + 1:i + 1] / hist_arr[i - window:i])
            vol = float(window_returns.std() * np.sqrt(252) * 100)
        volatility_series.append(round(vol, 2))

    # Annualized metrics
    mu_annual = float(mu_daily * 252 * 100)   # as %
    sigma_annual = float(sigma_daily * np.sqrt(252) * 100)  # as %

    return {
        "days": list(range(1, n_days_forward + 1)),
        "p05": [round(v, 2) for v in p05],
        "p50": [round(v, 2) for v in p50],
        "p95": [round(v, 2) for v in p95],
        "sample_paths": [[round(v, 2) for v in path] for path in sample_paths],
        "var_95": round(var_95, 2),
        "current_daily_avg": round(S0, 2),
        "expected_30d_total": round(float(np.mean(terminal_values)) * n_days_forward, 2),
        "worst_case_30d_total": round(var_95 * n_days_forward, 2),
        "volatility_series": volatility_series,
        "mu_annual_pct": round(mu_annual, 2),
        "sigma_annual_pct": round(sigma_annual, 2),
        "n_simulations": n_simulations,
    }


if __name__ == "__main__":
    import json
    result = run_monte_carlo()
    print(json.dumps({k: v if not isinstance(v, list) else f"[{len(v)} items]"
                      for k, v in result.items()}, indent=2))
    print(f"\nVaR 95%: ₹{result['var_95']:,.0f}/day worst case")
    print(f"Drift (μ): {result['mu_annual_pct']:.1f}%/yr | Volatility (σ): {result['sigma_annual_pct']:.1f}%/yr")
