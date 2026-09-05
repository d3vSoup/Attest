# Attest — Project Summary

## What We Did
- **Restored the "Bloomberg Terminal" Aesthetic**: Re-enabled the original React-based dashboard (with Instrument Serif & IBM Plex Mono) and the FastAPI backend (`server.py`). The dashboard runs at `http://localhost:8001`.
- **Integrated Real Data Pipeline**: Created `data/load_real_data.py` to seamlessly ingest the Kaggle `mlg-ulb/creditcardfraud` dataset. It handles Kaggle API downloads, standardizes the metadata, and prepares it for the pipeline.
- **Implemented Live Tamper Detection Demo**: Built `demo/tamper_test.py` (Phase 12 of the pitch) which:
  1. Retrieves anchored, verified decisions from the SQLite DB.
  2. Silently corrupts N records (simulating direct DB writes by a malicious insider).
  3. Re-runs verification, proving the cryptographic hashes instantly catch 100% of the tampered records with 0% false positives.
- **Fixed Model Retraining Pipeline**: Added automated scripts to retrain the XGBoost classifier and the Isolation Forest anomaly detector on the newly ingested Kaggle data so the AI agents use realistic distributions.

## Architecture
- **Frontend**: React 18 (CDN-loaded, no build step) with custom CSS in `frontend/index.html`.
- **Backend**: FastAPI (`server.py`) exposing the Groq-powered endpoints and SQLite decision logs.
- **On-chain Validation**: Merkle roots of batched decisions are written to the Polygon Amoy testnet (`contracts/Attest.sol` + `attest/chain.py`).

## Next Steps (If Applicable)
- Wire the tamper-test buttons directly into the React UI to run the demo visually.
- Enhance the Chat interface to retrieve data specific to the live Kaggle transactions.
