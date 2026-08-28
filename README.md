# Attest — AI Payment Intelligence

> Every payment decision your system makes is explainable, bounded, and provably unaltered.

```
Attest Score = AI classification
             + policy gate check        ← is this action allowed?
             + anomaly flag             ← does this look like anything we've seen before?
             + blockchain proof         ← did anyone touch this record after the fact?
```

A failed payment is not just an error. It is a moment that branches: retry and recover the revenue, flag and investigate the fraud, escalate and protect the customer. Attest makes every one of those branches legible — to the merchant, to the regulator, and to the judge auditing the system three years from now.

Built for the Razorpay AI Buildathon.

---

## Meet Priya

Priya runs a B2B SaaS company out of Bengaluru. Her product has 340 paying customers. She collects through Razorpay.

Every week, she sees roughly **15 failed payments** in her dashboard. All of them look identical: *"Payment Failed."*

She doesn't know which 12 were fraud attempts by stolen cards and which 3 were genuine customers who hit a gateway timeout at 2 AM. She retries all 15. The fraud attempts chargeback. The genuine customers — annoyed by the second charge attempt — churn.

**What Attest gives Priya:**

| Payment | Attest says | Action taken | Outcome |
|---|---|---|---|
| Card from new IP, 3AM, ₹49,000 | `fraud_flag · anomaly=TRUE · confidence 0.94` | Escalate → human review | Chargeback avoided |
| Axis gateway timeout, known customer | `gateway_timeout · anomaly=FALSE · confidence 0.89` | Auto-retry after 4 hours | Payment recovered |
| Insufficient funds, salary-cycle pattern | `insufficient_funds · anomaly=FALSE · confidence 0.91` | Nudge alt payment method | Customer retained |
| 3DS auth failure, foreign card | `auth_3ds_failure · anomaly=TRUE · confidence 0.77` | Block + notify Priya | Fraud caught |

Every one of those decisions is:
- Hashed with SHA-256 the moment it is made
- Batched into a Merkle tree every hour
- Anchored on the **Polygon Amoy blockchain** — permanently, immutably
- Verifiable by Priya, her auditors, or Razorpay compliance — at any time

If anyone — including Attest itself — alters a decision record after the fact, the next verification run catches it immediately. This is not a claim. **You can watch it fail live** (see the demo below).

---

## The identity, precisely

```
For every payment event e:

  decision(e) ∈ {retry, discount, alt_payment_nudge, escalate, block}

  where:
    classifier_output = XGBoost(features(e))         → class + confidence
    anomaly_score     = IsolationForest(features(e))  → normal | anomaly
    policy_gate       = policy.yaml constraints        → allowed | out_of_bounds
    chain_anchor      = SHA256(record) → Merkle root → Polygon Amoy tx

  and:
    decision is BLOCKED if policy_gate fails, regardless of classifier confidence
    decision is ESCALATED if anomaly_score = anomaly AND confidence < 0.80
    every branch is recorded before it executes, not after
```

The policy file (`policy.yaml`) is itself anchored on-chain before any decisions run. Altering the rules post-anchor causes policy verification to fail — the same way altering a decision record does.

---

## What it actually does — phase by phase

### Phase 1 · Data ingestion
Real transaction data from the [Kaggle Credit Card Fraud dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) (284,807 transactions, 492 fraud cases). Mapped to Razorpay-style failure classes: `insufficient_funds`, `auth_3ds_failure`, `gateway_timeout`, `fraud_flag`.

### Phase 2 · AI classification (XGBoost)
Trained on 10,000 transactions with stratified class balancing. The model outputs a **failure class and a confidence score** for every event. It does not make the decision alone — it feeds the policy gate.

**Honest numbers:**
```
AUC-ROC             0.926
Brier score         0.0009   (0 = perfect calibration)
ECE                 < 0.003  (expected calibration error)
Base fraud rate     0.17% of transactions
```

### Phase 3 · Anomaly detection (Isolation Forest)
Trained separately on the same data. Flags events that look unlike anything in the training distribution — novel fraud patterns, unusual velocity, card-not-present with new device fingerprint. Runs **before** the classifier, not after.

**Honest limitation:** The anomaly detector misses approximately **23% of novel fraud patterns in the first 24 hours** of a new attack vector — before enough examples accumulate to shift the distribution. It is not a real-time learner. We report this rather than averaging it away, because the 24-hour exposure window is exactly when it matters most. The mitigation is escalation: any `anomaly=TRUE` decision below 0.80 confidence goes to a human.

### Phase 4 · Policy engine
Every candidate decision is checked against `policy.yaml` before execution:
- Max discount: 10%
- Max retries: 3 per event
- Escalation threshold: confidence < 0.60
- Allowed actions: `retry | discount | alt_payment_nudge | escalate`

Decisions that violate policy are blocked, logged with reason `POLICY_VIOLATION`, and escalated. The policy file is hashed at startup and anchored on-chain — so a future change to the rules is detectable, not just auditable.

### Phase 5 · Decision recording
Every decision is written to SQLite as an immutable record:
```json
{
  "record_id":   "4e7b3053-1c3a-...",
  "record_type": "action",
  "decision":    "retry",
  "confidence":  0.891,
  "is_anomaly":  false,
  "policy_check": "PASS",
  "sha256":      "a3f7d2c1...",
  "timestamp":   "2026-08-28T08:14:33Z"
}
```

### Phase 6 · Blockchain anchoring (Polygon Amoy)
Records are batched hourly. Each batch is Merkle-hashed and the root is written to `Attest.sol` on Polygon Amoy testnet. The contract stores:
```solidity
mapping(uint256 => bytes32) public merkleRoots;
```
Any record can be verified against the on-chain root at any time — without trusting the Attest server.

### Phase 7 · Verification & tamper detection
```bash
python verifier/verify_all.py
```
Replays every stored record, recomputes its SHA-256, and compares against the stored hash. A mismatch means the record was altered after anchoring.

### Phase 8 · Groq-powered AI agent chat
The dashboard includes a conversational agent (powered by Groq LLaMA) that answers questions about any payment event in natural language:
> *"Why was this ₹49,000 payment escalated instead of retried?"*
> *"How many fraud flags came from UPI in the last hour?"*
> *"Show me the blockchain proof for transaction 4e7b3053."*

### Phase 9 · Risk analytics suite
Four live tabs powered by real data:

| Tab | Model | Output |
|---|---|---|
| **Monte Carlo** | GBM (1,000 paths × 30 days) | VaR at P05, P50/P95 settlement fan chart, rolling volatility |
| **Fraud Diffusion** | SIR epidemiological model | R₀ per payment channel, contagion curve, containment ratio |
| **Probability Calibration** | Platt scaling + reliability diagram | Brier score, ECE, per-channel calibration gap |
| **Live Pipeline** | SHA-256 → Merkle → Amoy | Real-time view of every record flowing through the audit pipeline |

---

## The tamper-detection demo (Phase 12)

This is the 90 seconds that proves everything else.

```bash
# Clean slate — run from scratch
python demo/tamper_test.py --reset

# If the pipeline has already run
python demo/tamper_test.py
```

What happens:
1. The script retrieves 5 anchored, cryptographically verified decisions from the database
2. It silently overwrites their `decision` fields — simulating a malicious insider or a database breach
3. It re-runs the verifier
4. Every tampered record is caught: `HASH_MISMATCH — record was altered post-anchoring`
5. Untouched records continue to show: `VERIFIED`

**The catch rate is 100% with 0 false positives.** Not because we tuned it — because SHA-256 is deterministic. There is nothing to tune.

This is the answer to *"how do we prove the AI didn't just change its mind after the fact?"*

---

## What Razorpay gets from this

| Problem | Attest answer |
|---|---|
| *Merchants claim the AI made a wrong decision* | Every decision has a hash, a timestamp, and a blockchain anchor. Show them the proof. |
| *A regulator asks why a payment was blocked* | Replay the record: classifier said `fraud_flag` at 0.94 confidence, anomaly detector agreed, policy gate confirmed. Here's the blockchain tx. |
| *A developer changed the fraud rules overnight* | Policy file is anchored. The changed version hashes differently. The audit trail shows exactly when the change happened. |
| *Novel fraud pattern arrives that the model hasn't seen* | Anomaly detector flags it even without a classification, routes to human review before it executes. |
| *A merchant wants to understand their payment failure patterns* | Monte Carlo VaR, SIR diffusion curve, per-channel calibration — live in the dashboard. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend  (React 18, CDN — no build step)              │
│  http://localhost:8001                                   │
│  Instrument Serif + IBM Plex Mono · Bloomberg terminal  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / REST
┌──────────────────────▼──────────────────────────────────┐
│  Backend  (FastAPI · server.py)                         │
│  ├── /api/decide          AI + policy gate              │
│  ├── /api/stats           dashboard counters            │
│  ├── /api/monte-carlo     GBM simulation                │
│  ├── /api/fraud-sir       SIR model                     │
│  ├── /api/probability-calibration  reliability diagram  │
│  └── /api/live-pipeline   real-time audit stream        │
└──────┬───────────────┬────────────────┬─────────────────┘
       │               │                │
┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────────────────┐
│  XGBoost    │ │  Isolation  │ │  SQLite · audit log      │
│  classifier │ │  Forest     │ │  SHA-256 hashed records  │
│  ml/train_  │ │  anomaly    │ └──────┬──────────────────-┘
│  classifier │ │  detector   │        │ Merkle batch (hourly)
└─────────────┘ └─────────────┘ ┌──────▼──────────────────┐
                                 │  Polygon Amoy testnet   │
                                 │  contracts/Attest.sol   │
                                 │  merkleRoots[]          │
                                 └─────────────────────────┘
```

**Stack:** Python 3.11 · FastAPI · XGBoost · scikit-learn · SQLite · Groq LLaMA 3.1 · Web3.py · Solidity · Chart.js · React 18

---

## Honest numbers

| Metric | Value | Note |
|---|---|---|
| Classifier AUC-ROC | **0.926** | Kaggle creditcardfraud, stratified split |
| Brier score | **0.0009** | 0 = perfect; excellent calibration |
| Tamper catch rate | **100%** | SHA-256 is deterministic, not tunable |
| Tamper false positives | **0%** | A verified record that verifies is a verified record |
| Anomaly miss rate (novel vectors, 24h) | **~23%** | Reported, not averaged away. Mitigation: escalation. |
| Policy gate | **hard block** | No ML confidence score overrides a policy violation |
| On-chain network | **Polygon Amoy** | Testnet only — no real funds at risk |

---

## How to run

```bash
# 1. Clone and set up
git clone https://github.com/d3vSoup/Attest.git
cd Attest/attest
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Add your API keys
cp .env.example .env
# Edit .env — add GROQ_API_KEY and (optional) POLYGON_RPC_URL + PRIVATE_KEY

# 3. Load real data and train models
python data/load_real_data.py          # downloads Kaggle dataset
python ml/train_classifier.py          # trains XGBoost
python ml/train_anomaly.py             # trains Isolation Forest

# 4. Run the tamper demo (the 90-second proof)
python demo/tamper_test.py --reset     # clean slate
python demo/tamper_test.py             # if pipeline already ran

# 5. Start the dashboard
python server.py
# → http://localhost:8001
```

**For judges running the demo live:**
```bash
python demo/tamper_test.py --reset
# Watch: 5 records VERIFIED → 5 records corrupted → 5 records HASH_MISMATCH
# The blockchain anchor is what makes those mismatches provable
```

---

## Project structure

```
attest/
├── server.py              # FastAPI backend — all endpoints
├── policy.yaml            # Decision bounds (anchored on-chain at startup)
├── frontend/
│   └── index.html         # React 18 dashboard (CDN, no build step)
├── ml/
│   ├── train_classifier.py    # XGBoost training
│   ├── train_anomaly.py       # Isolation Forest training
│   ├── monte_carlo.py         # GBM settlement simulation
│   ├── sir_model.py           # Fraud diffusion model
│   └── calibration.py         # Probability calibration (Platt scaling)
├── demo/
│   └── tamper_test.py         # Phase 12 — the 90-second proof
├── verifier/
│   └── verify_all.py          # SHA-256 replay verifier
├── contracts/
│   └── Attest.sol             # Solidity contract — Polygon Amoy
├── attest/
│   ├── agent.py               # AI decision loop (classifier + anomaly + policy)
│   └── chain.py               # Web3 anchoring layer
├── data/
│   └── load_real_data.py      # Kaggle ingest + standardisation
└── db/
    └── attest.db              # SQLite audit log
```

---

## Why the blockchain isn't theatre

The most common objection to blockchain audit trails is: *"you could just use a database with immutable writes."*

You could. But an immutable database is only as trustworthy as the people who control the database server. Polygon Amoy is controlled by nobody in this room.

The contract stores one thing: a Merkle root. It doesn't store decisions, customer data, or anything sensitive. It stores a 32-byte fingerprint of a batch of decisions. That fingerprint can be recomputed by anyone with the original records — and if it doesn't match what's on-chain, the records were altered.

The threat model this addresses is not hackers. It is **institutional pressure** — the moment someone asks an engineering team to quietly change a payment outcome that was already made. The audit trail makes that impossible to do invisibly.

---

## What we'd build next

1. **Real-time anomaly model updates** — streaming new fraud signals into the Isolation Forest without a full retrain, closing the 23% 24-hour gap
2. **Per-merchant policy profiles** — Priya's SaaS has different risk tolerance than a hyperlocal grocery store; the policy engine should know
3. **Webhook delivery with proof** — when Attest sends a decision webhook to Priya's system, it includes the SHA-256 and the block number so she can verify the decision herself without calling Attest
4. **Regulatory export** — one-click PDF of the full audit trail for a transaction, formatted for RBI dispute resolution

---

## Acknowledgements

Dataset: [MLG-ULB Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) — 284,807 real transactions, European cardholders, September 2013.

The anomaly miss rate and calibration numbers are measured on held-out data, not training data. The 23% miss rate for novel fraud vectors in the first 24 hours is a structural limitation of static Isolation Forest models, not a tuning artifact — we report it because hiding it would make the system look better than it is, and judges should know what they're looking at.

*Built at the Razorpay AI Buildathon, 2026.*
