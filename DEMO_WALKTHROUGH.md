# Attest — Complete Demo Walkthrough

> How to show this to a judge, investor, or anyone who's never seen it.
> Read-time: ~10 min. Demo-time: 5–8 min if you move confidently.

---

## Before you start

```bash
cd attest/
source venv/bin/activate
python server.py    # → http://localhost:8001
```

Open http://localhost:8001 in Chrome, full-screen.

---

## The 15-second opening line (say this before touching anything)

> "Priya runs a SaaS company with 340 customers on Razorpay. Every week she gets 15 failed
> payments. All say 'Payment Failed.' She can't tell which 12 are fraud and which 3 are real
> customers who hit a gateway error at 2 AM. She retries all 15. The fraudulent ones chargeback.
> The real ones — annoyed by the second charge attempt — churn. Attest solves that. And it
> proves, cryptographically, that it solved it correctly, forever."

---

## SECTION 1 — The Header Bar

Walk left → right.

### "Attest · AI Payment Intelligence"
- Serif font = intentional gravitas. Bloomberg Terminal aesthetic.
- "AI Payment Intelligence" — one level above "fraud detection."

### ⬡ Analytics button (purple)
- Opens the risk intelligence suite. Come back to this later.

### Right-side counters
| Counter | What it means |
|---|---|
| 152 DECISIONS | Total AI decisions since pipeline ran |
| 147/152 VERIFIED | Decisions with valid blockchain-backed proof |
| 0 RISK FLAGS | Decisions anomaly-flagged by Isolation Forest |
| ● LIVE (green pulse) | Dashboard is live-connected to FastAPI backend |

Say: "147 of 152 decisions are cryptographically verified against Polygon. The 5 unverified
ones are what we're about to corrupt in the demo."

---

## SECTION 2 — Left Sidebar (Activity Feed)

### Coloured dots = failure class
| Colour | Class | Meaning |
|---|---|---|
| 🔴 Red | fraud_flag | AI: likely fraudulent |
| 🟠 Orange | gateway_timeout | Payment rail timed out — not the customer's fault |
| 🟡 Amber (pulsing) | anomaly_alert | Isolation Forest: statistically unusual |
| 🔵 Blue | auth_3ds_failure | 3D Secure authentication failed |

### "4 FAILED PAYMENTS"
Core merchant events. Click one — e.g., "UPI payment failed · Rahul Mehta · ₹850."

Each line shows:
- Bold name = failure description
- Name · Amount = customer + transaction value
- Timestamp in IBM Plex Mono monospace

### "1 RISK ALERTS"
Velocity anomaly — anomaly detector fired. The transaction pattern was out-of-distribution
for this customer before the classifier even ran.

### "2 CHARGEBACKS"
Retrospective. Someone already disputed. Shows the system has memory of outcomes.

### "RISK INTELLIGENCE"
Click "Open Analytics Suite" — second entry point to the analytics modal.

### "DEMO CONTROLS (PHASE 12)"
| Button | What it does |
|---|---|
| Run Tamper Test | Corrupts 5 records, re-runs verifier, shows HASH_MISMATCH |
| Load Kaggle Data | Resets DB, re-ingests real Kaggle fraud data (~30 seconds) |

---

## SECTION 3 — Centre Panel (AI Chat)

Click on a failed payment event in the sidebar.

### Context bar (top)
Shows which event is selected: type badge, customer name + amount, timestamp.

### Chat — example questions to type live

Q: "What happened with this payment?"
→ Failure class, confidence, action taken, policy result.

Q: "Was this fraud or a technical failure?"
→ anomaly=TRUE + fraud_flag → probably fraud. gateway_timeout without anomaly → technical.

Q: "What action did Attest take?"
→ Exact decision: retry / escalate / block — with reason from policy.yaml.

Q: "Show me the cryptographic proof for this decision"
→ SHA-256 hash + Polygon Amoy tx hash + block number.

Q: "Why wasn't this just retried?"
→ "Anomaly score was TRUE and confidence was 0.77, below escalation threshold of 0.80."

### Input placeholder
"Ask anything — settlement, fraud, recovery..." — not scripted. Any question is valid.

---

## SECTION 4 — Right Panel (Cryptographic Proof)

Only visible when an event is selected. This is the "blockchain isn't theatre" proof.

### What each field means
| Field | Meaning |
|---|---|
| Record ID | UUID identifying this decision in the audit log |
| SHA-256 Hash | Fingerprint of the exact record at moment of creation |
| Decision | retry / escalate / block / discount |
| Confidence | XGBoost classifier probability (e.g., 0.891 = 89.1%) |
| Anomaly | TRUE or FALSE — Isolation Forest verdict |
| Policy check | PASS or FAIL — within policy.yaml bounds |
| Block / Tx Hash | Polygon Amoy transaction where this Merkle root was written |
| ⛓ Chain link | Opens PolygonScan — verifiable by anyone, right now |

Say: "This hash can be recomputed from the raw record in SQLite. If those two values don't
match, the record was tampered with. That's the entire audit trail in one panel."

---

## SECTION 5 — Analytics Modal

Click ⬡ Analytics in the header.

---

### TAB 1: Monte Carlo

What you're looking at:
- 1,000 simulated 30-day settlement paths using Geometric Brownian Motion (GBM)
- Each coloured line = one simulation path — the fan chart
- Purple line = P50 median. Green dashed = P95 best case. Red dashed = P05 worst case (VaR).

Stat cards:
| Card | Meaning |
|---|---|
| Daily Avg Settlement | Current run-rate baseline |
| Settlement at Risk (P05) | Worst 5% of days — Value at Risk |
| 30-Day Expected Total | Median projection over 30 days |
| Annualised Volatility σ | How wildly settlement amounts swing |

Volatility bars below:
- Orange above 180%, red above 250% — elevated risk thresholds
- Tells Priya whether her settlement volume is predictable or chaotic

Say: "1,000 possible futures. In 95% of scenarios, monthly settlement is above ₹X. This
is the kind of financial intelligence no payment dashboard currently gives merchants."

---

### TAB 2: Fraud Diffusion (SIR)

What you're looking at:
- SIR epidemiological model — the same math as COVID spread modelling
- S = Susceptible (legit transactions). I = Infected (active fraud). R = Recovered (blocked).

Stat cards:
| Card | Meaning |
|---|---|
| Overall R₀ | Basic reproduction number. R₀ < 1 = fraud dying. R₀ > 1 = spreading. |
| Peak Infected | Maximum simultaneous active fraud in simulation |
| Total Population | Transactions across all channels |
| Containment Rate | % of fraud resolved by day 60 |

R₀ per channel bars:
- Red = R₀ > 1 (spreading). Blue = R₀ < 1 (contained).
- Shows which channels are riskier: UPI vs card vs netbanking vs wallet.

Say: "R₀ of 0.035 means for every fraud transaction, only 0.035 downstream become fraudulent.
Fraud is contained. This is a quantified claim, not an assertion."

---

### TAB 3: Probability Calibration

What you're looking at:
- Reliability diagram — gold standard for ML confidence trustworthiness
- Diagonal dashed line = perfect calibration (70% confidence = 70% actual fraud rate)
- Blue line = our XGBoost model. Tracks the diagonal = confidence scores are trustworthy.

Stat cards:
| Card | Meaning |
|---|---|
| Brier Score | 0 = perfect. Ours: 0.0009 — excellent. |
| ECE | Expected Calibration Error. < 0.003. |
| AUC-ROC | Discrimination power. 0.926. |
| Base Fraud Rate | How rare fraud is: 0.17% of transactions |

Per-channel table:
- Actual fraud rate vs model-predicted rate per channel
- Gap column: green = close. Red = needs attention.

Say: "When Attest says '89% confident,' that number is trustworthy. Brier 0.0009.
The policy gate relies on this being accurate — if confidence is inflated, the escalation
threshold means nothing."

---

### TAB 4: Live Pipeline

What you're looking at:
- Real-time stream of records flowing through the audit pipeline
- Updates every 4 seconds

Each row:
| Column | Meaning |
|---|---|
| Stage badge | processed / hashed / batched / anchored |
| Record ID | Truncated UUID |
| Record type | action (decision made) or escalation (human review) |
| Decision | retry / block / escalate — colour coded |
| ANOMALY / CLEAR | Red = Isolation Forest fired. Green = clear. |
| sha256:xxx | First bytes of SHA-256 |
| ⛓ Chain | Opens PolygonScan for anchored batches |

Pipeline header: PROCESS → SHA-256 HASH → MERKLE BATCH → POLYGON AMOY ANCHOR

Say: "Every 4 seconds, fresh decisions. You can see them going processed → hashed → batched →
anchored. The ⛓ icon means it's on-chain. Immutable. No one can change what that record said."

---

## SECTION 6 — Tamper Detection Demo ← MOST IMPORTANT

Close the modal. In sidebar under "DEMO CONTROLS (PHASE 12)", click "Run Tamper Test."

### Step 1 — Baseline (all clean)
```
ATTEST VERIFIER — 152 records checked
  ✅ Verified:  152
  ❌ Failed:    0
```

### Step 2 — Silent corruption
```
[tamper] Corrupting 5 records silently...
  record bb78d718... → changed decision: retry → block
  ...
```
Direct SQLite write. Bypasses the application entirely. Simulates: database breach,
rogue admin, legal order, insider threat.

### Step 3 — Re-verification
```
ATTEST VERIFIER — 152 records checked
  ✅ Verified:  147
  ❌ Failed:    5

  ❌ bb78d718...  HASH_MISMATCH — record was altered post-anchoring
  ❌ e0209c88...  HASH_MISMATCH
  ✅ 4e7b3053...  VERIFIED
```

Say: "5 records silently altered. Verifier caught all 5 immediately. 147 untouched records
still VERIFIED. 100% catch rate. 0 false positives. We didn't tune this — SHA-256 is
deterministic. A byte changed = hash changed. Nothing to tune."

Then: "This is the answer to 'how do we prove the AI didn't just change its mind after the
fact?' It can't. The blockchain anchor makes that impossible to do invisibly."

---

## SECTION 7 — Footer Bar

Thin strip at the bottom:
| Position | Content |
|---|---|
| Left | "Attest · AI Payment Intelligence · Razorpay AI Buildathon 2026" |
| Middle | "Groq · LLaMA 3.1" — the LLM |
| Right | "Polygon Amoy · Testnet · Forest" — chain + model |

Always say proactively: "Polygon Amoy testnet — no real funds. The cryptographic mechanism
is identical to mainnet. Testnet = no MATIC spent during development."

---

## The 5-minute condensed script

1. Open dashboard → header stats: "152 decisions, 147 verified, live"
2. Click a failed payment → right panel: hash, decision, confidence
3. Type in chat: "Why was this payment escalated?" → wait for response
4. Open Analytics → Monte Carlo → "1,000 simulated futures, VaR quantified"
5. Switch to SIR → "R₀ = 0.035, fraud is contained"
6. Close modal → Run Tamper Test → "147 verified → 5 corrupted → 5 caught. 100%."
7. Close: "Every payment: classified, policy-gated, anomaly-checked, hashed, anchored.
   Provably. Permanently."

---

## Judge questions — answers

Q: "How is this different from just logging?"
A: A log entry can be changed by whoever controls the log. A SHA-256 hash checked against
   a blockchain anchor cannot be changed without detection — by anyone, including Attest.

Q: "Why not use AWS QLDB?"
A: QLDB is controlled by Amazon. Polygon Amoy is controlled by nobody. The threat model
   is institutional pressure — someone asking engineering to quietly change a decision.
   QLDB doesn't protect against Amazon or Razorpay's own infra team.

Q: "23% miss rate — isn't that a problem?"
A: Yes, and we say so in the README. Mitigation: any anomaly below 0.80 confidence
   escalates to human review. The fix is real-time streaming updates — explicitly in
   our "what we'd build next" list.

Q: "Why XGBoost and not a neural network?"
A: Interpretability. "The model said so" isn't an answer in a payment dispute.
   "The model weighted velocity and card country 3x more than amount" is.
   Also: confidence scores need to be calibrated (Brier 0.0009) — neural networks
   without calibration layers often aren't.

Q: "Is the Groq chat reading the blockchain?"
A: Chat reads from SQLite (which mirrors what was anchored). For on-chain verification,
   the verifier script talks directly to the Polygon Amoy RPC. The chat gives you the
   hash and tx ID — verify on PolygonScan right now.

---

## Don't do these

❌ Don't start with analytics. Start with Priya's story.
❌ Don't say "blockchain makes it immutable" without showing the tamper demo immediately after.
❌ Don't apologise for the 23% miss rate. Own it. It proves you understand the system.
❌ Don't call it a "fraud detection system." It's payment intelligence + audit trail.
   Fraud detection is one output. Explainability and provability are the product.
✅ Mention "Polygon Amoy testnet — no real funds" before they ask.
✅ Let the tamper demo output finish before talking. The wall of VERIFIED/HASH_MISMATCH
   is dramatic. Let it land.
