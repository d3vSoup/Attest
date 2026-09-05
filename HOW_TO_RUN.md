# How to Run Attest for the Demo

This guide is for Judges and Presenters to run the full Razorpay AI Buildathon flow.

## 1. Setup & Environment
Ensure you have the required Python dependencies installed:
```bash
pip install -r requirements.txt
```
Set up your `.env` file with the required keys (Groq API, Kaggle API if fetching real data, etc.):
```bash
cp .env.example .env
```

## 2. Load Real Data & Run the ML Pipeline
To get a completely fresh start with real data (Kaggle Credit Card Fraud dataset), run the tamper test with the reset flag. This will:
- Clear the old SQLite database
- Download Kaggle data
- Retrain the anomaly & classifier models
- Run 500 records through the decision pipeline and anchor them to the blockchain
```bash
python demo/tamper_test.py --reset
```
*Note: If you already have `db/attest.db` populated, you can skip this step.*

## 3. Run the Dashboard (React UI + FastAPI)
Launch the main server to serve the React dashboard and Groq AI endpoints:
```bash
python server.py
```
Open **[http://localhost:8001](http://localhost:8001)** in your browser. You will see the live Attest UI with the "Bloomberg Terminal" aesthetic.

## 4. Run the Tamper Detection Demo (Phase 12)
To prove to the judges that the cryptographic audit trail works:
1. Ensure the server and pipeline have already processed records.
2. In a new terminal, run:
```bash
python demo/tamper_test.py
```
3. This script will silently corrupt 5 records in the SQLite database, mimicking an attacker.
4. It will immediately run the verifier (`verifier/verify.py`), which re-hashes the records, checks them against the on-chain Merkle root, and flags the tampered records as `HASH_MISMATCH`.
5. The script outputs a perfect scorecard proving 100% detection rate and 0% false positives.
