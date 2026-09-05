<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,20,24,30&height=220&section=header&text=ATTEST&fontSize=80&fontColor=ffffff&fontAlignY=40&desc=Payment%20Integrity%20%C2%B7%20AI%20Risk%20Intelligence%20%C2%B7%20Cryptographic%20Audit&descAlignY=62&descSize=13&descColor=cccccc&animation=twinkling&fontFamily=Courier%20New" width="100%"/>

<br/>

<p>
  <img src="https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/XGBoost-FF6600?style=for-the-badge&logo=xgboost&logoColor=white"/>
  <img src="https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white"/>
</p>
<p>
  <img src="https://img.shields.io/badge/Solidity-363636?style=for-the-badge&logo=solidity&logoColor=white"/>
  <img src="https://img.shields.io/badge/Polygon_Amoy-8247E5?style=for-the-badge&logo=polygon&logoColor=white"/>
  <img src="https://img.shields.io/badge/React_18-20232A?style=for-the-badge&logo=react&logoColor=61DAFB"/>
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white"/>
</p>
<p>
  <img src="https://img.shields.io/badge/API_Live-Render-46E3B7?style=for-the-badge&logo=render&logoColor=black"/>
  <img src="https://img.shields.io/badge/Frontend_Live-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white"/>
  <img src="https://img.shields.io/badge/License-MIT-8247E5?style=for-the-badge"/>
</p>

<br/>

<a href="https://attest-zpyl.vercel.app"><img src="https://img.shields.io/badge/%E2%86%92%20Live%20Dashboard-1a1a2e?style=flat-square&logoColor=white" height="28"/></a>
&nbsp;
<a href="https://attest-tw7o.onrender.com/docs"><img src="https://img.shields.io/badge/%E2%86%92%20API%20Docs-009688?style=flat-square&logoColor=white" height="28"/></a>
&nbsp;
<a href="https://github.com/d3vSoup/Attest"><img src="https://img.shields.io/badge/%E2%86%92%20GitHub-24292e?style=flat-square&logo=github&logoColor=white" height="28"/></a>

<br/><br/>

<img src="https://readme-typing-svg.demolab.com?font=Courier+New&size=16&duration=3000&pause=1000&color=8247E5&center=true&vCenter=true&multiline=false&width=700&lines=Every+payment+decision+is+explainable%2C+bounded%2C+and+provably+unaltered.;Fraud+that+spreads+like+a+network.+Attest+watches+the+system.;Cryptographic+proof.+Not+a+claim.+Mathematical+certainty." alt="Typing SVG"/>

<br/><br/>

</div>

---

<div align="center">
<sub>B U I L T &nbsp; F O R &nbsp; T H E &nbsp; R A Z O R P A Y &nbsp; A I &nbsp; B U I L D A T H O N &nbsp; 2 0 2 6</sub>
</div>

<br/>

```
Attest Score  =  AI classification          XGBoost + Isolation Forest
              +  policy gate check          permitted bounds enforced before execution
              +  anomaly signal             unsupervised detection, no labels needed
              +  blockchain proof           Merkle root anchored on Polygon Amoy
```

<br/>

---

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=12&height=2&section=header" width="100%"/>
</div>

## &nbsp;The Problem

<br/>

Payment gateways are good at catching one bad transaction. They are not good at what happens next.

**Fraud spreads.** One compromised merchant node infects connected peers through shared processors and infrastructure. By the time anyone notices, it is already a network problem. Traditional tools watch individual transactions. Attest watches the system.

**Settlement is unpredictable.** Chargebacks arrive in waves. Processors hold the wrong amount of capital — too little gets you hit, too much is idle liquidity. Without a forward projection, you are always reacting.

**Audit trails can be silently altered.** When a dispute reaches Visa arbitration, transaction logs are assembled manually from a database that anyone with access can edit. There is no provable guarantee a record was not touched between when a decision was made and when it was reviewed.

<br/>

---

## &nbsp;Core Systems

<br/>

<table>
<tr>
<td width="50%" valign="top">

<img src="https://img.shields.io/badge/01-Cryptographic%20Audit%20Trail-8247E5?style=flat-square" height="22"/>

<br/><br/>

Every decision is SHA-256 hashed the moment it is made. Records are batched hourly into a Merkle tree. The root is anchored permanently on **Polygon Amoy** via a Solidity smart contract.

Any post-facto change to any record causes the next verification run to fail with `HASH_MISMATCH`. Catch rate: 100%. Not because it was tuned — because SHA-256 is deterministic.

```solidity
mapping(uint256 => bytes32) public merkleRoots;
```

</td>
<td width="50%" valign="top">

<img src="https://img.shields.io/badge/02-Dual--Layer%20AI%20Engine-FF6600?style=flat-square" height="22"/>

<br/><br/>

**Isolation Forest** runs first — unsupervised, no labels needed. It assigns an anomaly score to every incoming transaction before the classifier sees it.

**XGBoost** then attributes root cause across four failure classes: velocity spike, card-not-present fraud, account takeover, gateway timeout. Outputs a calibrated confidence score per payment channel.

</td>
</tr>
<tr>
<td width="50%" valign="top">

<img src="https://img.shields.io/badge/03-SIR%20Contagion%20Model-009688?style=flat-square" height="22"/>

<br/><br/>

Applies the Susceptible-Infected-Recovered epidemiological framework to merchant networks. A single compromised node is patient zero.

The model projects fraud spread over 7, 14, and 30-day windows — giving processors advance warning before contagion peaks, using the same mathematical structure used to model disease outbreaks.

</td>
<td width="50%" valign="top">

<img src="https://img.shields.io/badge/04-Monte%20Carlo%20Risk%20Engine-3776AB?style=flat-square" height="22"/>

<br/><br/>

Runs 1,000+ stochastic simulations on settlement portfolios, varying chargeback rates, dispute outcomes, and transaction volumes.

Outputs a 30-day liquidity risk projection with P05/P50/P95 confidence intervals — so processors know exactly how much capital buffer to hold under worst-case scenarios.

</td>
</tr>
</table>

<br/>

---

## &nbsp;Honest Numbers

<br/>

<div align="center">

| Metric | Value | Note |
|:---|:---:|:---|
| Classifier AUC-ROC | ![0.926](https://img.shields.io/badge/0.926-8247E5?style=flat-square) | Kaggle creditcardfraud, stratified split |
| Brier Score | ![0.0009](https://img.shields.io/badge/0.0009-009688?style=flat-square) | 0 is perfect — excellent calibration |
| Cross-validated F1 | ![0.775](https://img.shields.io/badge/0.775_%C2%B10.010-FF6600?style=flat-square) | 5-fold weighted average |
| Tamper catch rate | ![100%](https://img.shields.io/badge/100%25-2ea44f?style=flat-square) | SHA-256 is deterministic, nothing to tune |
| False positives | ![0%](https://img.shields.io/badge/0%25-2ea44f?style=flat-square) | A verified record that verifies is verified |
| Novel vector miss rate (first 24h) | ![~23%](https://img.shields.io/badge/~23%25-e11d48?style=flat-square) | Reported — not averaged away |
| On-chain network | ![Polygon Amoy](https://img.shields.io/badge/Polygon_Amoy-8247E5?style=flat-square) | Testnet only, no real funds at risk |

</div>

<br/>

> The 23% miss rate for novel fraud vectors in the first 24 hours is a structural limitation of a static Isolation Forest — it requires enough new examples to shift the training distribution. It is reported here because obscuring it would make the system appear more capable than it is. Mitigation: any `anomaly=TRUE` decision below 0.80 confidence is auto-escalated to human review.

<br/>

---

## &nbsp;Architecture

<br/>

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend  (React 18, CDN — no build step)                          │
│  Instrument Serif  +  IBM Plex Mono  ·  Bloomberg terminal UI       │
│  Deployed: Vercel  →  https://attest-zpyl.vercel.app               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  HTTP / REST
┌──────────────────────────▼──────────────────────────────────────────┐
│  Backend  (FastAPI · server.py)                                      │
│  Deployed: Render  →  https://attest-tw7o.onrender.com              │
│  Cold-start model training via startup.py on first deploy           │
│                                                                      │
│  /api/decide                    AI classification + policy gate      │
│  /api/stats                     Dashboard counters                   │
│  /api/monte-carlo               GBM simulation (1,000 paths)        │
│  /api/fraud-sir                 SIR contagion model                 │
│  /api/probability-calibration   Reliability diagram + Brier score   │
│  /api/live-pipeline             Real-time audit stream              │
└──────┬────────────────┬──────────────────┬──────────────────────────┘
       │                │                  │
┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼──────────────────────────┐
│  XGBoost    │  │  Isolation  │  │  SQLite  ·  Audit Log             │
│  Classifier │  │  Forest     │  │  SHA-256 hashed decision records  │
│  + SHAP     │  │  Anomaly    │  └───────┬──────────────────────────-┘
└─────────────┘  └─────────────┘          │  Merkle batch (hourly)
                                  ┌────────▼─────────────────────────┐
                                  │  Polygon Amoy Testnet            │
                                  │  contracts/Attest.sol            │
                                  │  merkleRoots[]  ·  immutable     │
                                  └──────────────────────────────────┘
```

<br/>

<div align="center">

<img src="https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/XGBoost-FF6600?style=flat-square"/>
<img src="https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikit-learn&logoColor=white"/>
<img src="https://img.shields.io/badge/SHAP-363636?style=flat-square"/>
<img src="https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white"/>
<img src="https://img.shields.io/badge/Groq_LLaMA_3-00A67E?style=flat-square"/>
<img src="https://img.shields.io/badge/Web3.py-F16822?style=flat-square&logo=ethereum&logoColor=white"/>
<img src="https://img.shields.io/badge/Solidity-363636?style=flat-square&logo=solidity&logoColor=white"/>
<img src="https://img.shields.io/badge/Chart.js-FF6384?style=flat-square&logo=chart.js&logoColor=white"/>
<img src="https://img.shields.io/badge/React_18-20232A?style=flat-square&logo=react&logoColor=61DAFB"/>

</div>

<br/>

---

## &nbsp;Project Structure

<br/>

```
attest/
├── server.py                    FastAPI backend, all API endpoints
├── startup.py                   Cold-start model training for Render deploy
├── policy.yaml                  Decision bounds, anchored on-chain at startup
│
├── frontend/
│   └── index.html               React 18 dashboard (CDN, no build step)
│
├── ml/
│   ├── train_classifier.py      XGBoost training + SHAP explainability
│   ├── train_anomaly.py         Isolation Forest training
│   ├── monte_carlo.py           GBM settlement simulation
│   ├── sir_model.py             SIR fraud contagion model
│   └── calibration.py          Probability calibration (Platt scaling)
│
├── demo/
│   └── tamper_test.py           Live tamper detection proof
│
├── verifier/
│   └── verify_all.py            SHA-256 Merkle replay verifier
│
├── contracts/
│   └── Attest.sol               Solidity contract — Polygon Amoy
│
└── attest/
    ├── agent.py                 AI decision loop
    └── chain.py                 Web3 anchoring layer
```

<br/>

---

## &nbsp;Why the Blockchain Is Not Theatre

<br/>

The most common objection: *you could just use a database with immutable writes.*

You could. But an immutable database is only as trustworthy as the people who control the database server.

The Attest contract stores one thing: a 32-byte Merkle root. No decisions, no customer data, nothing sensitive. That fingerprint can be recomputed by anyone with the original records. If it does not match what is on-chain, the records were altered. The threat model is not external hackers — it is **institutional pressure**: the moment someone asks an engineering team to quietly modify a payment outcome that has already been recorded. The audit trail makes that invisible change impossible.

<br/>

---

## &nbsp;What Would Come Next

<br/>

<table>
<tr>
<td><img src="https://img.shields.io/badge/01-Streaming%20Anomaly%20Updates-8247E5?style=flat-square"/></td>
<td>Ingesting new fraud signals into the Isolation Forest without a full retrain — closing the 23% first-24-hour gap</td>
</tr>
<tr>
<td><img src="https://img.shields.io/badge/02-Per--merchant%20Policy%20Profiles-FF6600?style=flat-square"/></td>
<td>Risk tolerance differs between a B2B SaaS and a hyperlocal grocery store — the policy engine should know</td>
</tr>
<tr>
<td><img src="https://img.shields.io/badge/03-Webhook%20Delivery%20with%20Proof-009688?style=flat-square"/></td>
<td>Decision webhooks include the SHA-256 and block number so merchants can self-verify without calling Attest</td>
</tr>
<tr>
<td><img src="https://img.shields.io/badge/04-Regulatory%20Export-3776AB?style=flat-square"/></td>
<td>One-click PDF of the full audit trail formatted for RBI dispute resolution</td>
</tr>
</table>

<br/>

---

## &nbsp;Acknowledgements

<br/>

Dataset: [MLG-ULB Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) — 284,807 real transactions, European cardholders, September 2013.

All reported metrics are measured on held-out data, not training data. The 23% novel-vector miss rate is a structural limitation of static Isolation Forest models, not a tuning artifact.

<br/>

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,20,24,30&height=120&section=footer&animation=twinkling" width="100%"/>

<sub>Built at the Razorpay AI Buildathon 2026 &nbsp;·&nbsp; <a href="https://github.com/d3vSoup/Attest">github.com/d3vSoup/Attest</a></sub>

</div>
