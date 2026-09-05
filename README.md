<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0f0f0f&height=200&section=header&text=ATTEST&fontSize=72&fontColor=ffffff&fontAlignY=38&desc=Payment%20Integrity%20%C2%B7%20AI%20Risk%20Intelligence%20%C2%B7%20Cryptographic%20Audit&descAlignY=58&descSize=14&descColor=888888&animation=fadeIn&fontFamily=Courier%20New" width="100%" alt="Attest header"/>

<br/>

[![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-FF6600?style=flat-square&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io)
[![Solidity](https://img.shields.io/badge/Solidity-363636?style=flat-square&logo=solidity&logoColor=white)](https://soliditylang.org)
[![Polygon](https://img.shields.io/badge/Polygon_Amoy-8247E5?style=flat-square&logo=polygon&logoColor=white)](https://polygon.technology)
[![React](https://img.shields.io/badge/React_18-20232A?style=flat-square&logo=react&logoColor=61DAFB)](https://reactjs.org)
[![Deployed on Render](https://img.shields.io/badge/API-Render-46E3B7?style=flat-square&logo=render&logoColor=white)](https://attest-tw7o.onrender.com)
[![Frontend on Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://attest-zpyl.vercel.app)
[![License](https://img.shields.io/badge/License-MIT-555555?style=flat-square)](LICENSE)

<br/>

<a href="https://attest-zpyl.vercel.app">Live Dashboard</a> &nbsp;·&nbsp;
<a href="https://attest-tw7o.onrender.com/docs">API Docs</a> &nbsp;·&nbsp;
<a href="https://github.com/d3vSoup/Attest">GitHub</a>

<br/><br/>

</div>

---

<div align="center">
<sub><sup>BUILT FOR THE RAZORPAY AI BUILDATHON 2026</sup></sub>
</div>

<br/>

```
Attest Score  =  AI classification
              +  policy gate check       is this action within permitted bounds?
              +  anomaly signal          does this look like anything seen before?
              +  blockchain proof        did anyone touch this record after the fact?
```

> A failed payment is not just an error. It is a moment that branches: retry and recover the revenue, flag and investigate the fraud, escalate and protect the customer. Attest makes every one of those branches legible — to the merchant, to the regulator, and to the auditor reviewing the system three years from now.

<br/>

---

## The Problem

Payment gateways are good at catching one bad transaction. They are not good at what happens next.

**Fraud spreads.** One compromised merchant node infects connected peers through shared processors and infrastructure. By the time anyone notices, it is already a network problem. Traditional tools watch individual transactions. Attest watches the system.

**Settlement is unpredictable.** Chargebacks arrive in waves. Processors hold the wrong amount of capital — too little gets you hit, too much is idle liquidity. Without a forward projection, you are always reacting.

**Audit trails can be altered.** When a dispute reaches Visa arbitration, transaction logs are assembled manually from a database that anyone with access can edit. There is no way to prove a record was not touched between when the decision was made and when it was reviewed.

Attest solves all three.

<br/>

---

## What It Does

<table>
<tr>
<td width="50%" valign="top">

### Cryptographic Audit Trail

Every decision is SHA-256 hashed the moment it is made. Records are batched hourly into a Merkle tree and the root is anchored permanently on the **Polygon Amoy testnet** via a Solidity smart contract.

Any post-facto change to any record — including by Attest itself — causes the next verification run to fail with `HASH_MISMATCH`. The catch rate is 100%. Not because it was tuned — because SHA-256 is deterministic.

</td>
<td width="50%" valign="top">

### Dual-Layer AI Engine

**Isolation Forest** runs first — unsupervised, no labels needed. It flags transactions that look unlike anything in the training distribution before the classifier sees them.

**XGBoost classifier** then attributes root cause: velocity spike, card-not-present fraud, account takeover, gateway timeout, insufficient funds. Outputs a failure class and a calibrated confidence score per payment channel.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### SIR Fraud Contagion Model

Uses the Susceptible-Infected-Recovered epidemiological framework to simulate fraud propagation across merchant networks. A single compromised node is patient zero. The model projects spread over 7, 14, and 30 days — giving processors advance warning before contagion peaks.

</td>
<td width="50%" valign="top">

### Monte Carlo Risk Simulation

Runs 1,000+ stochastic simulations on settlement portfolios, varying chargeback rates, dispute outcomes, and transaction volumes. Outputs a 30-day liquidity risk projection with P05/P50/P95 confidence intervals so processors know exactly how much capital buffer to hold.

</td>
</tr>
</table>

<br/>

---

## Honest Numbers

| Metric | Value | Notes |
|---|---|---|
| Classifier AUC-ROC | **0.926** | Kaggle creditcardfraud dataset, stratified split |
| Brier Score | **0.0009** | 0 is perfect; indicates excellent probability calibration |
| Cross-validated F1 | **0.775 ± 0.010** | 5-fold, weighted |
| Tamper catch rate | **100%** | SHA-256 is deterministic — nothing to tune |
| False positives | **0%** | A verified record that verifies is a verified record |
| Anomaly miss rate (novel vectors, first 24h) | **~23%** | Reported, not averaged away. Mitigation: auto-escalation |
| On-chain network | **Polygon Amoy** | Testnet only — no real funds at risk |

The 23% miss rate for novel fraud vectors in the first 24 hours is a structural limitation of a static Isolation Forest — it requires enough new examples to shift the training distribution before it catches a new attack pattern. It is reported here because obscuring it would make the system appear more capable than it is.

<br/>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend  (React 18, CDN — no build step)                      │
│  Instrument Serif + IBM Plex Mono   ·   Bloomberg terminal UI   │
│  Deployed: Vercel                                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP / REST
┌──────────────────────────▼──────────────────────────────────────┐
│  Backend  (FastAPI · server.py)                                 │
│  Deployed: Render (cold-start model training via startup.py)    │
│  ├── /api/decide               AI + policy gate                 │
│  ├── /api/stats                dashboard counters               │
│  ├── /api/monte-carlo          GBM simulation                   │
│  ├── /api/fraud-sir            SIR contagion model              │
│  ├── /api/probability-calibration   reliability diagram         │
│  └── /api/live-pipeline        real-time audit stream           │
└──────┬────────────────┬─────────────────┬───────────────────────┘
       │                │                 │
┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────────────────────┐
│  XGBoost    │  │  Isolation  │  │  SQLite  ·  audit log        │
│  Classifier │  │  Forest     │  │  SHA-256 hashed records      │
└─────────────┘  └─────────────┘  └──────┬───────────────────────┘
                                          │  Merkle batch (hourly)
                                   ┌──────▼───────────────────────┐
                                   │  Polygon Amoy testnet        │
                                   │  contracts/Attest.sol        │
                                   │  merkleRoots[]               │
                                   └──────────────────────────────┘
```

**Stack:** Python 3.11 · FastAPI · XGBoost · scikit-learn · SHAP · SQLite · Groq LLaMA 3 · Web3.py · Solidity · Chart.js · React 18

<br/>

---

## Project Structure

```
attest/
├── server.py                   FastAPI backend, all endpoints
├── startup.py                  Cold-start model training for Render deploy
├── policy.yaml                 Decision bounds, anchored on-chain at startup
├── frontend/
│   └── index.html              React 18 dashboard (CDN, no build step)
├── ml/
│   ├── train_classifier.py     XGBoost training + SHAP explainability
│   ├── train_anomaly.py        Isolation Forest training
│   ├── monte_carlo.py          GBM settlement simulation
│   ├── sir_model.py            Fraud diffusion model
│   └── calibration.py         Probability calibration (Platt scaling)
├── demo/
│   └── tamper_test.py          90-second live tamper detection proof
├── verifier/
│   └── verify_all.py           SHA-256 replay verifier
├── contracts/
│   └── Attest.sol              Solidity contract — Polygon Amoy
├── attest/
│   ├── agent.py                AI decision loop
│   └── chain.py                Web3 anchoring layer
└── data/
    └── load_real_data.py       Kaggle ingest + standardisation
```

<br/>

---

## Running Locally

```bash
# 1. Clone and set up environment
git clone https://github.com/d3vSoup/Attest.git
cd Attest/attest
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
# Add GROQ_API_KEY and (optional) POLYGON_RPC_URL + PRIVATE_KEY

# 3. Train models
python ml/train_classifier.py
python ml/train_anomaly.py

# 4. Run the tamper demo
python demo/tamper_test.py --reset

# 5. Start the server
python server.py
# Dashboard available at http://localhost:8001
```

**For judges:** Step 4 is the 90-second proof. Watch five records go from `VERIFIED` to `HASH_MISMATCH` after a silent in-place corruption — then back to `VERIFIED` after reset.

<br/>

---

## Why the Blockchain Is Not Theatre

The most common objection to blockchain audit trails: *you could just use a database with immutable writes.*

You could. But an immutable database is only as trustworthy as the people who control the database server.

The contract stores one thing: a 32-byte Merkle root. No decisions, no customer data, nothing sensitive. That fingerprint can be recomputed by anyone with the original records. If it does not match what is on-chain, the records were altered. The threat model is not external hackers — it is **institutional pressure**, the moment someone asks an engineering team to quietly modify a payment outcome that was already recorded. The audit trail makes that invisible change impossible.

<br/>

---

## What Would Come Next

- **Streaming anomaly updates** — ingesting new fraud signals into the Isolation Forest without a full retrain, closing the 23% first-24-hour gap
- **Per-merchant policy profiles** — risk tolerance differs between a B2B SaaS and a hyperlocal grocery store
- **Webhook delivery with proof** — decision webhooks include the SHA-256 hash and block number so merchants can self-verify without calling Attest
- **Regulatory export** — one-click PDF of the full audit trail for a transaction, formatted for RBI dispute resolution

<br/>

---

## Acknowledgements

Dataset: [MLG-ULB Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) — 284,807 real transactions, European cardholders, September 2013.

All reported metrics are measured on held-out data, not training data.

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0f0f0f&height=100&section=footer&animation=fadeIn" width="100%" alt="footer"/>
<sub>Built at the Razorpay AI Buildathon 2026</sub>
</div>
