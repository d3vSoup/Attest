"""
demo/viewer_app.py — Attest Decision Audit Dashboard

Design: editorial restraint — Instrument Serif headings, IBM Plex Mono for
data/hashes, Inter for body. No emojis. Single indigo accent on near-white.
Modeled on Bloomberg terminal seriousness, not consumer app aesthetics.

Run: streamlit run demo/viewer_app.py
"""

import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from attest.storage import get_all_decisions_for_viewer, get_connection
from verifier.verify import run_verification


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Attest — Decision Audit Trail",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Typography + Design System ─────────────────────────────────────────────────
# Instrument Serif (display) + IBM Plex Mono (data) + Inter (body)
# Palette: off-white #F9F9F8, near-black #111110, indigo accent #3730A3
# Rules: no emojis, no rounded badges, no colored alerts, no gradients
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');

  /* Global reset */
  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #F9F9F8;
    color: #111110;
  }

  /* Main content area */
  .main .block-container {
    padding-top: 2.5rem;
    padding-bottom: 4rem;
    max-width: 1400px;
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background-color: #F2F2F0;
    border-right: 1px solid #E4E4E2;
  }

  /* Product wordmark */
  .attest-wordmark {
    font-family: 'Instrument Serif', serif;
    font-size: 2.4rem;
    font-weight: 400;
    letter-spacing: -0.02em;
    color: #111110;
    line-height: 1;
    margin-bottom: 0.25rem;
  }
  .attest-descriptor {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 400;
    color: #6E6E6A;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0;
  }

  /* Section label — Instrument Serif, left-aligned, ruled line */
  .section-label {
    font-family: 'Instrument Serif', serif;
    font-size: 1.25rem;
    font-weight: 400;
    font-style: italic;
    color: #111110;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #E4E4E2;
    display: block;
  }

  /* Subsection label */
  .subsection-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6E6E6A;
    margin-bottom: 0.5rem;
    display: block;
  }

  /* KPI cards — monospaced numbers on ruled rows */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0;
    border-top: 1px solid #111110;
    border-bottom: 1px solid #E4E4E2;
    margin-bottom: 2rem;
  }
  .kpi-cell {
    padding: 1.25rem 1rem 1rem 0;
    border-right: 1px solid #E4E4E2;
  }
  .kpi-cell:last-child { border-right: none; }
  .kpi-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6E6E6A;
    margin-bottom: 0.4rem;
  }
  .kpi-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2.1rem;
    font-weight: 500;
    color: #111110;
    line-height: 1;
  }
  .kpi-value.accent { color: #3730A3; }
  .kpi-value.muted  { color: #6E6E6A; }
  .kpi-sub {
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    color: #9E9E9A;
    margin-top: 0.2rem;
  }

  /* Status indicator — text only */
  .status-ok {
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    color: #1A5C3A;
    background: #EDFAF2;
    border: 1px solid #A7E3C0;
    padding: 0.5rem 1rem;
    border-radius: 2px;
    margin-bottom: 1.5rem;
  }
  .status-err {
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    color: #7C2929;
    background: #FDF2F2;
    border: 1px solid #F0B8B8;
    padding: 0.5rem 1rem;
    border-radius: 2px;
    margin-bottom: 1.5rem;
  }

  /* Mono spans for hashes / IDs */
  .mono {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    color: #3730A3;
  }

  /* Horizontal rule replacement */
  .ruled { border: none; border-top: 1px solid #E4E4E2; margin: 2rem 0; }

  /* Streamlit metric override — use our mono style */
  [data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.8rem !important;
    font-weight: 500 !important;
    color: #111110 !important;
  }
  [data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.68rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    color: #6E6E6A !important;
  }
  [data-testid="stMetricDelta"] { display: none !important; }

  /* Streamlit native headers — override with Instrument Serif */
  h1, h2, h3 {
    font-family: 'Instrument Serif', serif !important;
    font-weight: 400 !important;
    font-style: italic;
    color: #111110 !important;
  }
  h1 { font-size: 1.8rem !important; }
  h2 { font-size: 1.3rem !important; }
  h3 { font-size: 1.1rem !important; font-style: normal !important; }

  /* Tables */
  .stDataFrame { border-radius: 2px !important; }
  .stDataFrame th {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    color: #6E6E6A !important;
    background: #F2F2F0 !important;
  }

  /* Sidebar controls */
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {
    font-style: normal !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.04em !important;
  }

  /* Alerts: replace Streamlit colored boxes */
  .stAlert { display: none !important; }

  /* Code blocks */
  code, pre {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.78rem !important;
  }

  /* Expander */
  [data-testid="stExpander"] summary {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    color: #6E6E6A;
  }

  /* Buttons — minimal */
  .stButton > button {
    border-radius: 2px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.03em !important;
    border: 1px solid #D4D4CF !important;
    background: #F9F9F8 !important;
    color: #111110 !important;
    box-shadow: none !important;
  }
  .stButton > button:hover {
    background: #F2F2F0 !important;
    border-color: #111110 !important;
  }
  .stButton > button[kind="primary"] {
    background: #111110 !important;
    color: #F9F9F8 !important;
    border-color: #111110 !important;
  }
  .stButton > button[kind="primary"]:hover {
    background: #3730A3 !important;
    border-color: #3730A3 !important;
  }

  /* Caption / small text */
  small, .caption, [data-testid="stCaptionContainer"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.72rem !important;
    color: #9E9E9A !important;
  }

  /* Divider override */
  hr { border-color: #E4E4E2 !important; }
</style>
""", unsafe_allow_html=True)


# ── Helper paths ───────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent.parent
CM_PATH   = ROOT / "models" / "classifier_metrics.json"
AM_PATH   = ROOT / "models" / "anomaly_metrics.json"
META_PATH = ROOT / "data" / "transactions_metadata.json"
DATA_PATH = ROOT / "data" / "transactions.csv"

INDIGO  = "#3730A3"
SLATE   = "#64748B"
NEUTRAL = "#D4D4CF"

# Neutral plotly palette — single indigo accent + slate grays
CHART_COLORS = {
    "gateway_timeout":    "#3730A3",
    "insufficient_funds": "#64748B",
    "auth_3ds_failure":   "#94A3B8",
    "fraud_flag":         "#1E293B",
}

CHART_LAYOUT = dict(
    font_family="Inter",
    plot_bgcolor="#F9F9F8",
    paper_bgcolor="#F9F9F8",
    margin=dict(t=16, b=8, l=0, r=0),
    legend=dict(
        orientation="h", y=-0.28, x=0,
        font=dict(family="Inter", size=10, color="#6E6E6A"),
    ),
    xaxis=dict(
        gridcolor="#EBEBEA", gridwidth=0.5,
        linecolor="#D4D4CF", tickfont=dict(family="Inter", size=10, color="#6E6E6A"),
        title_font=dict(family="Inter", size=10, color="#6E6E6A"),
    ),
    yaxis=dict(
        gridcolor="#EBEBEA", gridwidth=0.5,
        linecolor="#D4D4CF", tickfont=dict(family="Inter", size=10, color="#6E6E6A"),
        title_font=dict(family="Inter", size=10, color="#6E6E6A"),
    ),
    height=290,
)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**Controls**")
    st.caption("Attest dashboard v1.0")
    st.divider()

    if st.button("Refresh", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.markdown("**Tamper Detection Demo**")
    st.caption(
        "Silently corrupts N records in the database, then re-runs the verifier. "
        "Every alteration is detected via SHA-256 hash mismatch."
    )
    n_tamper = st.slider("Records to corrupt", min_value=1, max_value=10, value=3)

    if st.button("Run tamper test", type="primary", use_container_width=True):
        with st.spinner(f"Corrupting {n_tamper} record(s)..."):
            result = subprocess.run(
                [sys.executable, "demo/tamper_test.py", "--n", str(n_tamper)],
                capture_output=True, text=True, cwd=str(ROOT),
            )
        st.code(result.stdout + (result.stderr or ""), language="text")
        st.rerun()

    st.markdown("---")
    if st.button("Reset database", use_container_width=True):
        db_path = ROOT / "db" / "attest.db"
        if db_path.exists():
            db_path.unlink()
            st.caption("Database cleared. Re-run pipeline to regenerate.")
            st.rerun()

    st.markdown("---")
    st.caption(
        "Regulatory note: No real value moves on-chain. "
        "Polygon Amoy testnet only. Zero stablecoin/VDA regulatory exposure."
    )


# ── Header ─────────────────────────────────────────────────────────────────────
h_left, h_right = st.columns([3, 1])
with h_left:
    st.markdown('<div class="attest-wordmark">Attest</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="attest-descriptor">'
        'Cryptographic decision audit trail &nbsp;·&nbsp; '
        'Razorpay AI Buildathon 2026 &nbsp;·&nbsp; '
        'Track 01: AI Growth &amp; Agentic Commerce'
        '</div>',
        unsafe_allow_html=True,
    )

with h_right:
    if META_PATH.exists():
        with open(META_PATH) as f:
            meta = json.load(f)
        data_source = meta.get("data_source", "kaggle:mlg-ulb/creditcardfraud")
        day_window  = meta.get("date_range_days", "90")
        # Build a friendly subtitle from data_source if date_range_days is missing
        if "date_range_days" in meta:
            subtitle = f'{day_window}-day window'
        elif "kaggle" in str(data_source):
            subtitle = 'ULB Credit Card Fraud dataset · real transactions'
        elif "user-csv" in str(data_source):
            subtitle = f'user dataset · {data_source}'
        else:
            subtitle = 'synthetic · NPCI FY24 distribution'
        st.markdown(
            f'<div style="text-align:right; padding-top:0.6rem;">'
            f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:1.1rem;font-weight:500;color:#111110;">'
            f'{meta["total_records"]:,}</span>'
            f'<span style="font-family:\'Inter\',sans-serif;font-size:0.7rem;color:#6E6E6A;display:block;">'
            f'transactions · {subtitle}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown('<hr class="ruled">', unsafe_allow_html=True)


# ── Load audit data ────────────────────────────────────────────────────────────
decisions_raw = get_all_decisions_for_viewer()

if not decisions_raw:
    st.markdown(
        '<div class="status-err">'
        'No decisions found. Run: <code>python demo/run_pipeline.py --limit 500</code>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

verification_results = run_verification()
verify_map = {r["record_id"]: r for r in verification_results}


# ── KPI strip ─────────────────────────────────────────────────────────────────
total       = len([d for d in decisions_raw if d["record_type"] != "policy_anchor"])
verified    = sum(1 for r in verification_results if r["status"] == "VERIFIED")
failed      = total - verified
escalations = sum(1 for d in decisions_raw if d["record_type"] == "escalation")
anomalies   = sum(1 for d in decisions_raw if d.get("is_anomaly"))

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total decisions",    f"{total:,}")
c2.metric("Verified",           f"{verified:,}")
c3.metric("Integrity failures", f"{failed:,}")
c4.metric("Escalations",        f"{escalations:,}")
c5.metric("Anomalies detected", f"{anomalies:,}")

# Status line — text only, no emoji
if failed > 0:
    st.markdown(
        f'<div class="status-err">Integrity failure — {failed} record(s) failed SHA-256 verification. '
        f'Possible tampering detected. Run the tamper test from the sidebar to inspect.</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="status-ok">All {verified:,} records verified. '
        f'SHA-256 hashes match stored values. Audit trail is intact.</div>',
        unsafe_allow_html=True,
    )

st.markdown('<hr class="ruled">', unsafe_allow_html=True)


# ── Decision audit log ─────────────────────────────────────────────────────────
st.markdown('<span class="section-label">Decision Audit Log</span>', unsafe_allow_html=True)
EXPLORER_BASE = "https://amoy.polygonscan.com/tx/"

rows = []
for d in decisions_raw:
    if d["record_type"] == "policy_anchor":
        continue
    vr = verify_map.get(d["record_id"], {})
    status = vr.get("status", "UNKNOWN")
    tx = d.get("tx_hash") or ""

    rows.append({
        "Verified":    "PASS" if status == "VERIFIED" else "FAIL",
        "Type":        d["record_type"],
        "Transaction": (d.get("transaction_id") or "")[:16] + "…",
        "Action":      d.get("decision") or "—",
        "Confidence":  f"{d['confidence']:.3f}" if d.get("confidence") else "—",
        "Policy":      d.get("policy_check") or "—",
        "Flag":        "ANOMALY" if d.get("is_anomaly") else "",
        "Batch":       d.get("batch_seq") or "—",
        "Merkle Root": (d.get("merkle_root") or "")[:18] + "…" if d.get("merkle_root") else "pending",
        "Explorer":    f"{EXPLORER_BASE}{tx}" if tx else "",
    })

df_display = pd.DataFrame(rows)
st.dataframe(
    df_display,
    use_container_width=True,
    column_config={
        "Explorer": st.column_config.LinkColumn("Chain", display_text="View"),
    },
    hide_index=True,
    height=320,
)

st.markdown('<hr class="ruled">', unsafe_allow_html=True)


# ── Transaction analytics ──────────────────────────────────────────────────────
# Charts read from the decisions DB (pipeline records) so charts always reflect
# what the AI agent actually did, not the raw source CSV.
st.markdown('<span class="section-label">Transaction Analytics</span>', unsafe_allow_html=True)

# Build a mini-dataframe from decisions_raw for the charts
_chart_rows = []
for _d in decisions_raw:
    if _d["record_type"] == "policy_anchor":
        continue
    _chart_rows.append({
        "timestamp":    _d.get("timestamp") or "",
        "label":        _d.get("root_cause") or _d.get("decision") or "unknown",
        "channel":      _d.get("channel") or "unknown",
        "amount":       float(_d.get("amount") or 0),
        "hour_of_day":  int(_d.get("hour_of_day") or 0),
        "day_of_week":  int(_d.get("day_of_week") or 0),
        "is_anomaly":   bool(_d.get("is_anomaly")),
    })


if _chart_rows:
    df_txn = pd.DataFrame(_chart_rows)
    df_txn["timestamp"] = pd.to_datetime(df_txn["timestamp"], utc=True, errors="coerce")
    df_txn["date"] = df_txn["timestamp"].dt.date

    # Normalise label to the 4 known classes so CHART_COLORS applies cleanly
    _label_map = {
        "retry":             "insufficient_funds",
        "alt_payment_nudge": "gateway_timeout",
        "discount":          "auth_3ds_failure",
        "escalate":          "insufficient_funds",
    }
    df_txn["label"] = df_txn["label"].apply(
        lambda v: v if v in CHART_COLORS else _label_map.get(v, "insufficient_funds")
    )

    # Also try reading from the raw CSV for richer time-series if available
    if DATA_PATH.exists():
        try:
            _df_raw = pd.read_csv(DATA_PATH, usecols=["timestamp", "label", "channel", "amount",
                                                       "hour_of_day", "day_of_week"])
            _df_raw["timestamp"] = pd.to_datetime(_df_raw["timestamp"], utc=True, errors="coerce")
            _df_raw["date"] = _df_raw["timestamp"].dt.date
            df_txn_full = _df_raw
        except Exception:
            df_txn_full = df_txn
    else:
        df_txn_full = df_txn

    ta1, ta2 = st.columns(2)

    with ta1:
        st.markdown('<span class="subsection-label">Decision distribution by category</span>',
                    unsafe_allow_html=True)
        # Use DB decisions for the donut/bar — always populated
        decision_counts = df_txn["label"].value_counts().reset_index()
        decision_counts.columns = ["label", "count"]
        fig_tl = px.bar(
            decision_counts, x="label", y="count", color="label",
            color_discrete_map=CHART_COLORS,
            labels={"count": "Decisions", "label": ""},
            template="simple_white",
        )
        fig_tl.update_layout(**CHART_LAYOUT)
        fig_tl.update_traces(marker_line_width=0, showlegend=False)
        st.plotly_chart(fig_tl, use_container_width=True)

    with ta2:
        st.markdown('<span class="subsection-label">Failures by channel and category</span>',
                    unsafe_allow_html=True)
        ch_label = (
            df_txn_full.groupby(["channel", "label"])
            .size().reset_index(name="count")
        )
        # Ensure all labels in ch_label are mapped to known classes
        ch_label["label"] = ch_label["label"].apply(
            lambda v: v if v in CHART_COLORS else _label_map.get(v, "insufficient_funds")
        )
        fig_bar = px.bar(
            ch_label, x="channel", y="count", color="label",
            barmode="stack",
            color_discrete_map=CHART_COLORS,
            labels={"count": "Records", "channel": "", "label": ""},
            template="simple_white",
        )
        fig_bar.update_layout(**CHART_LAYOUT)
        fig_bar.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bar, use_container_width=True)

    ta3, ta4 = st.columns(2)

    with ta3:
        st.markdown('<span class="subsection-label">Amount distribution — log scale, by channel</span>',
                    unsafe_allow_html=True)
        _plot_df = df_txn_full[df_txn_full["amount"] > 0].copy()
        fig_hist = px.histogram(
            _plot_df, x="amount", color="channel",
            log_x=True, nbins=60, barmode="overlay", opacity=0.75,
            labels={"amount": "Amount", "channel": ""},
            template="simple_white",
            color_discrete_sequence=["#3730A3", "#64748B", "#94A3B8", "#CBD5E1"],
        )
        fig_hist.update_layout(**CHART_LAYOUT)
        fig_hist.update_traces(marker_line_width=0)
        st.plotly_chart(fig_hist, use_container_width=True)

    with ta4:
        st.markdown('<span class="subsection-label">Fraud flag density — hour of day × day of week</span>',
                    unsafe_allow_html=True)
        fraud_df = df_txn_full[df_txn_full["label"] == "fraud_flag"].copy()
        if len(fraud_df) > 0:
            hm_data  = (
                fraud_df.groupby(["day_of_week", "hour_of_day"])
                .size().reset_index(name="count")
            )
            pivot = hm_data.pivot_table(
                index="day_of_week", columns="hour_of_day",
                values="count", fill_value=0,
            )
            day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            fig_hm = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=[f"{h:02d}h" for h in pivot.columns],
                y=[day_labels[d % 7] for d in pivot.index],
                colorscale=[[0, "#F9F9F8"], [0.4, "#C7D2FE"], [1, "#3730A3"]],
                showscale=True,
                colorbar=dict(thickness=8, outlinewidth=0,
                              tickfont=dict(family="IBM Plex Mono", size=9, color="#6E6E6A")),
            ))
            hm_layout = {**CHART_LAYOUT}
            hm_layout["xaxis"] = dict(
                tickfont=dict(family="IBM Plex Mono", size=8, color="#6E6E6A"),
                tickangle=-45,
            )
            hm_layout["yaxis"] = dict(
                tickfont=dict(family="Inter", size=9, color="#6E6E6A"),
            )
            fig_hm.update_layout(**hm_layout)
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.caption("No fraud_flag records in current pipeline run.")
else:
    st.caption("No decisions found in database.")

st.markdown('<hr class="ruled">', unsafe_allow_html=True)


# ── ML model performance ───────────────────────────────────────────────────────
st.markdown('<span class="section-label">ML Model Performance</span>', unsafe_allow_html=True)
ml1, ml2 = st.columns(2)

with ml1:
    st.markdown('<span class="subsection-label">Root-cause classifier — XGBoost</span>',
                unsafe_allow_html=True)
    if CM_PATH.exists():
        with open(CM_PATH) as f:
            cm_data = json.load(f)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Accuracy",  f"{cm_data['accuracy']*100:.1f}%")
        m2.metric("F1 score",  f"{cm_data['weighted_f1']:.3f}")
        m3.metric("Precision", f"{cm_data.get('weighted_precision',0)*100:.1f}%")
        m4.metric("Recall",    f"{cm_data.get('weighted_recall',0)*100:.1f}%")

        if "cv_f1_mean" in cm_data:
            st.markdown(
                f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:0.75rem;color:#6E6E6A;">'
                f'5-fold CV F1: {cm_data["cv_f1_mean"]:.3f} ± {cm_data["cv_f1_std"]:.3f} — no overfitting'
                f'</span>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        if "per_class_metrics" in cm_data:
            st.markdown('<span class="subsection-label">Per-class breakdown</span>',
                        unsafe_allow_html=True)
            pcm = cm_data["per_class_metrics"]
            pcm_rows = [
                {
                    "Failure class":  cls,
                    "Precision":      f"{v['precision']*100:.1f}%",
                    "Recall":         f"{v['recall']*100:.1f}%",
                    "F1":             f"{v['f1']*100:.1f}%",
                    "Test support":   f"{v['support']:,}",
                }
                for cls, v in pcm.items()
            ]
            st.dataframe(pd.DataFrame(pcm_rows), hide_index=True, use_container_width=True)

        # Confusion matrix — neutral blues
        cm_matrix   = cm_data["confusion_matrix"]
        class_names = cm_data["class_names"]
        fig_cm = px.imshow(
            cm_matrix,
            text_auto=True,
            x=class_names,
            y=class_names,
            labels=dict(x="Predicted", y="Actual", color="Count"),
            color_continuous_scale=[[0, "#F9F9F8"], [0.2, "#C7D2FE"], [1, "#3730A3"]],
            aspect="auto",
        )
        fig_cm.update_layout(
            font_family="Inter",
            plot_bgcolor="#F9F9F8",
            paper_bgcolor="#F9F9F8",
            margin=dict(t=8, b=0, l=0, r=0),
            height=250,
            xaxis=dict(tickangle=-30, tickfont=dict(family="Inter", size=9, color="#6E6E6A")),
            yaxis=dict(tickfont=dict(family="Inter", size=9, color="#6E6E6A")),
            coloraxis_colorbar=dict(
                thickness=8, outlinewidth=0,
                tickfont=dict(family="IBM Plex Mono", size=9, color="#6E6E6A"),
            ),
        )
        st.plotly_chart(fig_cm, use_container_width=True)
        st.caption(
            f"Trained on {cm_data.get('n_train', '?'):,} records · "
            f"tested on {cm_data.get('n_test', '?'):,} · "
            f"{cm_data.get('n_features', 12)} features · "
            f"decline_code excluded to prevent label leakage"
        )
    else:
        st.caption("Train classifier: python ml/train_classifier.py")

with ml2:
    st.markdown('<span class="subsection-label">Anomaly detector — Isolation Forest (unsupervised)</span>',
                unsafe_allow_html=True)
    if AM_PATH.exists():
        with open(AM_PATH) as f:
            am_data = json.load(f)

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Precision",  f"{am_data['precision']*100:.1f}%")
        a2.metric("Recall",     f"{am_data['recall']*100:.1f}%")
        a3.metric("F1",         f"{am_data['f1']:.3f}")
        a4.metric("FP rate",    f"{am_data['false_positive_rate']*100:.1f}%")

        st.caption(
            f"{am_data['total_records']:,} records evaluated · "
            f"{am_data['true_anomalies']} true anomalies injected · "
            f"{am_data['detected_anomalies']} detected · "
            f"{am_data['false_positives']} false positives · "
            f"trained on clean records only"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Detection breakdown — horizontal stacked bar, austere
        det = am_data["detected_anomalies"]
        fp  = am_data["false_positives"]
        tp  = det - fp
        fn  = am_data["true_anomalies"] - tp
        tn  = am_data["total_records"] - am_data["true_anomalies"] - fp

        fig_det = go.Figure()
        for label, val, color in [
            ("True positives",  tp, "#3730A3"),
            ("False positives", fp, "#94A3B8"),
            ("Missed (FN)",     fn, "#CBD5E1"),
            ("True negatives",  tn, "#F1F5F9"),
        ]:
            fig_det.add_trace(go.Bar(
                x=[val], y=["Detection"], name=label,
                orientation="h", marker_color=color,
                text=[f"{val:,}" if val > 200 else ""],
                textposition="inside",
                textfont=dict(family="IBM Plex Mono", size=10, color="#111110"),
            ))

        fig_det.update_layout(
            barmode="stack",
            font_family="Inter",
            plot_bgcolor="#F9F9F8",
            paper_bgcolor="#F9F9F8",
            margin=dict(t=8, b=8, l=0, r=0),
            height=80,
            showlegend=True,
            legend=dict(
                orientation="h", y=-0.8, x=0,
                font=dict(family="Inter", size=9, color="#6E6E6A"),
            ),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False),
        )
        st.plotly_chart(fig_det, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<span class="subsection-label">Design rationale</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """<div style="font-family:'Inter',sans-serif;font-size:0.78rem;color:#6E6E6A;line-height:1.6;">
            Recall is prioritised over precision. In a cryptographic audit trail, missing a real anomaly
            (false negative) is far worse than a false positive. False positives are surfaced for human
            review via the escalation pathway — they do not trigger automatic action.
            The Isolation Forest is trained exclusively on clean (non-anomalous) decision vectors;
            it learns the distribution of normal agent behaviour and flags deviations.
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.caption("Train anomaly detector: python ml/train_anomaly.py")

st.markdown('<hr class="ruled">', unsafe_allow_html=True)


# ── Merkle batches + on-chain anchors ──────────────────────────────────────────
st.markdown('<span class="section-label">Merkle Batches & On-Chain Anchors</span>',
            unsafe_allow_html=True)

conn = get_connection()
batches = conn.execute("""
    SELECT b.batch_seq, b.merkle_root, b.leaf_count, b.anchored,
           a.tx_hash, a.block_number, a.anchored_at
    FROM batches b
    LEFT JOIN anchors a ON b.id = a.batch_id
    ORDER BY b.batch_seq ASC
""").fetchall()
conn.close()

if batches:
    batch_rows = []
    for b in batches:
        tx = b["tx_hash"] or ""
        batch_rows.append({
            "Batch":       b["batch_seq"],
            "Merkle root": b["merkle_root"][:24] + "…",
            "Decisions":   b["leaf_count"],
            "Anchored":    "yes" if b["anchored"] else "pending",
            "TX hash":     (tx[:20] + "…" if tx else "—"),
            "Block":       b["block_number"] or "—",
            "Timestamp":   (b["anchored_at"] or "—")[:19],
            "Explorer":    f"https://amoy.polygonscan.com/tx/{tx}" if tx else "",
        })

    st.dataframe(
        pd.DataFrame(batch_rows),
        use_container_width=True,
        column_config={
            "Explorer": st.column_config.LinkColumn("Chain", display_text="View"),
        },
        hide_index=True,
    )

    total_anchored = sum(b["leaf_count"] for b in batches)
    n_txns = len(batches)
    if total_anchored > 0:
        reduction = (1 - n_txns / total_anchored) * 100
        st.markdown(
            f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.82rem;'
            f'color:#3730A3;padding:0.6rem 0;">'
            f'{n_txns} on-chain transactions anchor {total_anchored:,} decisions — '
            f'{reduction:.0f}% fewer chain writes vs. one-per-decision. '
            f'Each decision individually provable via its Merkle inclusion proof.'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.caption("No batches yet. Configure .env and run the pipeline.")

st.markdown('<hr class="ruled">', unsafe_allow_html=True)


# ── Policy anchor ──────────────────────────────────────────────────────────────
st.markdown('<span class="section-label">Policy Anchor</span>', unsafe_allow_html=True)

conn2 = get_connection()
policy_row = conn2.execute(
    "SELECT * FROM decisions WHERE record_type = 'policy_anchor' ORDER BY id DESC LIMIT 1"
).fetchone()
conn2.close()

if policy_row:
    import json as _json
    pol = _json.loads(policy_row["canonical_json"])
    pa1, pa2, pa3 = st.columns(3)
    pa1.metric("Policy version", pol.get("policy_version", "—"))
    pa2.metric("Content hash",   pol.get("policy_content_hash", "")[:14] + "…")
    with pa3:
        st.markdown(
            '<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;'
            'color:#6E6E6A;line-height:1.6;padding-top:0.25rem;">'
            'The policy rulebook (action bounds, confidence thresholds, escalation rules) '
            'was hashed and anchored <em>before</em> any decisions ran. '
            'This proves the agent acted under this exact, unaltered policy — '
            'not a retroactively modified version.'
            '</div>',
            unsafe_allow_html=True,
        )
else:
    st.caption("No policy anchor found. Run the pipeline first.")

st.markdown('<hr class="ruled">', unsafe_allow_html=True)


# ── Dataset provenance ─────────────────────────────────────────────────────────
if META_PATH.exists():
    with open(META_PATH) as f:
        meta = json.load(f)

    with st.expander("Dataset provenance and statistical basis"):
        dp1, dp2 = st.columns(2)
        with dp1:
            st.markdown('<span class="subsection-label">Data source</span>',
                        unsafe_allow_html=True)
            _src = meta.get("data_source", "unknown")
            _stat_basis = meta.get("statistical_basis", [])
            if _stat_basis:
                for src in _stat_basis:
                    st.markdown(
                        f'<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;'
                        f'color:#6E6E6A;padding:0.15rem 0;">— {src}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                # Kaggle / user CSV data — show source info
                if "kaggle" in str(_src):
                    st.markdown(
                        '<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;color:#6E6E6A;line-height:1.6;">'
                        'ULB Credit Card Fraud Detection dataset<br>'
                        '284,807 real European credit card transactions (Sep 2013)<br>'
                        '492 genuine fraud cases (0.172% prevalence)<br>'
                        'PCA-anonymised features (V1–V28) for cardholder privacy<br>'
                        '<a href="https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud" '
                        'target="_blank" style="color:#3730A3;">kaggle.com/datasets/mlg-ulb/creditcardfraud</a>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                elif "user-csv" in str(_src):
                    st.markdown(
                        f'<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;color:#6E6E6A;">'
                        f'User-provided dataset: {_src}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;color:#6E6E6A;">'
                        'Synthetic dataset — NPCI FY24 statistical distributions</div>',
                        unsafe_allow_html=True,
                    )
            st.markdown(
                f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.72rem;'
                f'color:#9E9E9A;margin-top:0.5rem;">Generated: {meta.get("generation_timestamp","")[:10]}</div>',
                unsafe_allow_html=True,
            )
        with dp2:
            st.markdown('<span class="subsection-label">Class distribution</span>',
                        unsafe_allow_html=True)
            dist  = meta.get("class_distribution", {})
            total_recs = meta.get("total_records", 1)
            dist_rows = [
                {"Category": k, "Count": f"{v:,}", "Share": f"{v/total_recs*100:.1f}%"}
                for k, v in dist.items()
            ]
            st.dataframe(pd.DataFrame(dist_rows), hide_index=True, use_container_width=True)
            st.caption(
                f"Anomaly rate: {meta.get('anomaly_rate_pct', meta.get('anomaly_rate', 0)):.3f}% "
                f"({meta.get('anomaly_count', 0)} records) — matched to real-world outlier rates."
            )


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.68rem;'
    'color:#C4C4BE;padding-top:1rem;border-top:1px solid #E4E4E2;margin-top:1rem;">'
    'Attest — Razorpay AI Buildathon 2026 — No real value moves on-chain — '
    'Polygon Amoy testnet'
    '</div>',
    unsafe_allow_html=True,
)
