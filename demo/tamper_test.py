"""
demo/tamper_test.py

The centerpiece demo. Workflow:
  1. Run baseline verification (all records should be VERIFIED)
  2. Silently corrupt N records in SQLite (simulating an attacker)
  3. Re-run verifier — watch it catch every corruption immediately
  4. Print detection scorecard

Run AFTER demo/run_pipeline.py.
Usage: python demo/tamper_test.py [--n 5]
"""

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from attest.storage import get_connection, tamper_decision
from verifier.verify import run_verification

# Tamper scenarios: (field_dotpath, new_value)
# Each simulates a different kind of fraud/edit an attacker might make
TAMPER_SCENARIOS = [
    ("bounds_applied.max_discount_pct", "50"),    # inflated discount limit: 10 → 50
    ("decision", "discount"),                      # escalation hidden as discount
    ("confidence", "0.999"),                       # fake high-confidence injection
    ("timestamp", "2020-01-01T00:00:00+00:00"),   # backdated record
    ("decision", "retry"),                         # fraud_flag disguised as retry
]


def get_tamperable_records(n: int) -> list:
    """Fetch N anchored action/escalation records at random."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT d.record_id, d.record_type, d.decision, b.merkle_root
        FROM decisions d
        JOIN batches b ON d.batch_id = b.id
        WHERE d.record_type IN ('action', 'escalation')
        ORDER BY RANDOM()
        LIMIT ?
    """, (n,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def sep(char="=", width=60):
    print(char * width)


def main(n_tamper: int = 5):
    sep()
    print("ATTEST — LIVE TAMPER-DETECTION DEMO")
    sep()

    # ── Phase 1: Baseline ──────────────────────────────────────────────────────
    print("\n[Phase 1] Running baseline verification on all records...")
    time.sleep(0.4)
    baseline = run_verification()
    baseline_verified = sum(1 for r in baseline if r["status"] == "VERIFIED")

    if baseline_verified == 0:
        print("\nWARNING: No verified records found.")
        print("Run 'python demo/run_pipeline.py' first.")
        sys.exit(1)

    print(f"\n  ✅ Baseline: {baseline_verified}/{len(baseline)} records verified. All clean.")

    # ── Phase 2: Silent corruption ─────────────────────────────────────────────
    print(f"\n[Phase 2] Silently corrupting {n_tamper} records in the database...")
    print("  (Simulating an attacker editing stored decisions after anchoring)")
    time.sleep(0.8)

    records_to_tamper = get_tamperable_records(n_tamper)
    if not records_to_tamper:
        print("  No tamperable records found (need anchored decisions).")
        sys.exit(1)

    if len(records_to_tamper) < n_tamper:
        print(f"  Only {len(records_to_tamper)} tamperable records available.")
        n_tamper = len(records_to_tamper)

    tampered_ids = []
    for i, record in enumerate(records_to_tamper):
        field, new_value = TAMPER_SCENARIOS[i % len(TAMPER_SCENARIOS)]
        try:
            tamper_decision(record["record_id"], field, new_value)
            tampered_ids.append(record["record_id"])
            print(f"  ✏️  {record['record_id'][:12]}...  [{record['record_type']:12s}]"
                  f"  {field} → {new_value!r}")
        except Exception as e:
            print(f"  ⚠️  Skipping {record['record_id'][:12]}...: {e}")

    print(f"\n  {len(tampered_ids)} records corrupted silently. 🕵️  Nobody told the verifier.")
    time.sleep(0.8)

    # ── Phase 3: Detection ─────────────────────────────────────────────────────
    print(f"\n[Phase 3] Re-running verifier on all records...\n")
    time.sleep(0.4)
    post_results = run_verification()

    # ── Phase 4: Scorecard ─────────────────────────────────────────────────────
    sep()
    print("TAMPER-DETECTION SCORECARD")
    sep()

    detected   = sum(1 for r in post_results
                     if r["status"] in ("HASH_MISMATCH", "PROOF_INVALID")
                     and r["record_id"] in tampered_ids)
    false_pos  = sum(1 for r in post_results
                     if r["status"] not in ("VERIFIED", "NOT_ANCHORED")
                     and r["record_id"] not in tampered_ids)
    clean_recs = len(post_results) - len(tampered_ids)

    detection_rate = (detected / len(tampered_ids) * 100) if tampered_ids else 0.0
    fp_rate = (false_pos / max(1, clean_recs)) * 100

    print(f"\n  Records tampered:          {len(tampered_ids)}")
    print(f"  Tampers detected:          {detected}  ({detection_rate:.0f}%)")
    print(f"  False positives:           {false_pos}  ({fp_rate:.1f}%)")
    print(f"  Clean records still valid: {clean_recs - false_pos}")
    print(f"\n  Detection rate:  {detection_rate:.0f}%  ← target: 100%")
    print(f"  False-pos rate:  {fp_rate:.1f}%   ← target:   0%")

    if detection_rate == 100.0 and false_pos == 0:
        print("\n  🎯 PERFECT SCORE")
        print("     Every altered record was caught immediately.")
        print("     No clean records were incorrectly flagged.")
    else:
        print("\n  ⚠️  Some discrepancy — see individual results above.")

    sep()
    print("\nNote: Tampered records remain corrupted in db/attest.db.")
    print("      The Streamlit viewer will show them as ❌.")
    print("      To reset: rm db/attest.db && python demo/run_pipeline.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Attest Live Tamper Detection Demo")
    parser.add_argument("--n", type=int, default=5,
                        help="Number of records to corrupt (default: 5)")
    args = parser.parse_args()
    main(n_tamper=args.n)
