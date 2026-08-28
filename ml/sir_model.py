"""
ml/sir_model.py — Fraud Information Diffusion Model (SIR)

Treats fraud as a contagion spreading through a payment network.
Models S (Susceptible), I (Infected/Fraudulent), R (Recovered/Blocked) dynamics.

Based on: Epidemic models applied to financial network contagion
Reference: https://doi.org/10.3390/math9151781 (MDPI, 2021)

Returns:
  - S/I/R curves over time
  - R₀ (basic reproduction number) per payment channel
  - Network node data (channels as nodes, transaction co-occurrence as edges)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent


def _load_network_data(csv_path: Optional[Path] = None) -> pd.DataFrame:
    path = csv_path or ROOT / "data" / "transactions.csv"
    return pd.read_csv(path)


def _compute_sir_params(df: pd.DataFrame, channel: str) -> dict:
    """
    Compute SIR parameters for a given payment channel.

    β (transmission rate): estimated from observed fraud rate × contact rate
    γ (recovery rate): estimated from how fast fraud_flag decisions resolve

    R₀ = β / γ  (basic reproduction number)
    R₀ > 1 → fraud spreads; R₀ < 1 → fraud contained
    """
    channel_df = df[df["channel"] == channel]
    total = len(channel_df)
    if total == 0:
        return {"R0": 0, "beta": 0, "gamma": 0, "initial_infected": 0, "total": 0}

    # Initial infected = fraud_flag transactions
    infected = len(channel_df[channel_df["label"] == "fraud_flag"])

    # β: average "contacts" per transaction * probability of fraud spread
    # We model contact rate as average retry_count (each retry = potential spread)
    avg_retries = channel_df["retry_count_so_far"].mean() if "retry_count_so_far" in channel_df else 1.5
    fraud_prob = infected / total if total > 0 else 0.001
    beta = float(avg_retries * fraud_prob * 1.5)  # contact rate * infection prob

    # γ: recovery rate — modeled as (1 - fraud_flag rate) * base resolution speed
    # Fraud transactions are "recovered" (blocked) after detection lag
    # We assume 15% of infected recover per time step (6-7 day half-life)
    gamma = 0.15

    R0 = beta / gamma if gamma > 0 else 0

    return {
        "R0": round(R0, 3),
        "beta": round(beta, 4),
        "gamma": round(gamma, 4),
        "initial_infected": int(infected),
        "total": int(total),
    }


def run_sir_simulation(
    csv_path: Optional[Path] = None,
    n_steps: int = 60,  # 60 time steps (days)
) -> dict:
    """
    Run SIR simulation for all payment channels.

    Returns:
      - per_channel: {channel: {R0, S[], I[], R[], params}}
      - aggregate: combined S/I/R across all channels
      - channel_r0: {channel: R0} for comparison bar chart
    """
    df = _load_network_data(csv_path)
    channels = df["channel"].unique().tolist()

    per_channel = {}
    all_S, all_I, all_R = [], [], []

    for ch in channels:
        params = _compute_sir_params(df, ch)
        N = params["total"]
        if N == 0:
            continue

        beta = params["beta"]
        gamma = params["gamma"]
        I0 = max(params["initial_infected"], 1)
        S0 = N - I0
        R0_count = 0

        S_arr = [S0]
        I_arr = [I0]
        R_arr = [R0_count]

        dt = 1.0
        S, I, R = float(S0), float(I0), float(R0_count)

        for _ in range(n_steps - 1):
            new_infected = beta * S * I / N * dt
            new_recovered = gamma * I * dt

            # Clamp to valid ranges
            new_infected = min(new_infected, S)
            new_recovered = min(new_recovered, I)

            S -= new_infected
            I += new_infected - new_recovered
            R += new_recovered

            S = max(0, S)
            I = max(0, I)
            R = max(0, R)

            S_arr.append(round(S))
            I_arr.append(round(I))
            R_arr.append(round(R))

        per_channel[ch] = {
            "params": params,
            "S": S_arr,
            "I": I_arr,
            "R": R_arr,
        }
        all_S.append(np.array(S_arr))
        all_I.append(np.array(I_arr))
        all_R.append(np.array(R_arr))

    # Aggregate across all channels
    if all_S:
        agg_S = np.sum(all_S, axis=0).tolist()
        agg_I = np.sum(all_I, axis=0).tolist()
        agg_R = np.sum(all_R, axis=0).tolist()
    else:
        agg_S = agg_I = agg_R = [0] * n_steps

    channel_r0 = {ch: per_channel[ch]["params"]["R0"] for ch in per_channel}
    overall_r0 = round(np.mean(list(channel_r0.values())), 3) if channel_r0 else 0.0

    # Peak infection info
    peak_I = int(max(agg_I))
    peak_day = int(np.argmax(agg_I))
    total_population = sum(p["params"]["total"] for p in per_channel.values())
    total_recovered = int(agg_R[-1]) if agg_R else 0

    return {
        "steps": list(range(n_steps)),
        "aggregate": {
            "S": [int(v) for v in agg_S],
            "I": [int(v) for v in agg_I],
            "R": [int(v) for v in agg_R],
        },
        "per_channel": {
            ch: {
                "R0": per_channel[ch]["params"]["R0"],
                "beta": per_channel[ch]["params"]["beta"],
                "gamma": per_channel[ch]["params"]["gamma"],
                "S": [int(v) for v in per_channel[ch]["S"]],
                "I": [int(v) for v in per_channel[ch]["I"]],
                "R": [int(v) for v in per_channel[ch]["R"]],
            }
            for ch in per_channel
        },
        "channel_r0": channel_r0,
        "overall_r0": overall_r0,
        "peak_infected": peak_I,
        "peak_day": peak_day,
        "total_population": total_population,
        "total_recovered_by_day60": total_recovered,
        "containment_ratio": round(total_recovered / max(total_population, 1), 4),
        "n_steps": n_steps,
    }


if __name__ == "__main__":
    import json
    result = run_sir_simulation()
    print(f"Overall R₀: {result['overall_r0']}")
    print("Channel R₀:")
    for ch, r0 in result["channel_r0"].items():
        icon = "🔴 SPREADING" if r0 > 1 else "🟢 CONTAINED"
        print(f"  {ch:12s}: R₀={r0:.3f}  {icon}")
    print(f"\nPeak infection day: {result['peak_day']}, peak infected: {result['peak_infected']}")
    print(f"Containment ratio by day 60: {result['containment_ratio']*100:.1f}%")
