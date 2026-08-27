"""
demo/tamper_test.py  —  ATTEST LIVE TAMPER-DETECTION DEMO (Phase 12)

The single most important 90 seconds of the demo.

What it shows judges:
  1. Baseline verification — every record is VERIFIED
  2. Silent corruption    — we edit 5 records like an attacker would
  3. Re-verify           — the audit trail catches EVERY tamper instantly
  4. Scorecard           — detection 100%, false positives 0%

How it works:
  - tamper_decision() edits canonical_json in SQLite (simulates attacker with DB access)
  - verify_one() recomputes SHA-256 and compares to the sealed sha256_hex
  - Because sha256_hex was written at decision-time, ANY edit triggers HASH_MISMATCH

Run AFTER demo/run_pipeline.py (needs >= 10 anchored records).
Usage:
  python demo/tamper_test.py          # corrupt 5 records (default)
  python demo/tamper_test.py --n 3    # corrupt 3 records
  python demo/tamper_test.py --reset  # wipe db and re-run pipeline first
"""

import sys
import time
import argparse
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from attest.storage import get_connection, tamper_decision
from verifier.verify import run_verification

# ── ANSI colours (degrade gracefully if terminal doesn't support) ──────────────
try:
    import shutil
    _COLOUR = shutil.get_terminal_size().columns > 0
except Exception:
    _COLOUR = False

def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _COLOUR else text

GREEN  = lambda t: _c("92", t)
RED    = lambda t: _c("91", t)
YELLOW = lambda t: _c("93", t)
BOLD   = lambda t: _c("1",  t)
DIM    = lambda t: _c("2",  t)
CYAN   = lambda t: _c("96", t)


# ── Tamper scenarios — diverse, realistic, judge-friendly ──────────────────────
# Each entry: (field_dotpath, new_value, human_label)
# All fields are guaranteed present in EVERY action/escalation canonical record.
# IMPORTANT: values are chosen to always differ from the real value so the
# tamper always produces an actual byte change (no silent no-ops).
TAMPER_SCENARIOS = [
    (
        "decision",
        "discount",
        "Escalation relabelled as discount",
    ),
    (
        "confidence",
        "0.9990",
        "Fake high-confidence injection",
    ),
    (
        "agent_version",
        "attest-v0.1-patched",
        "Agent version string overwritten (provenance attack)",
    ),
    (
        "decision",
        "retry",
        "fraud_flag hidden as routine retry",
    ),
    (
        "timestamp",
        "2020-01-01T00:00:00+00:00",
        "Record backdated to pre-launch",
    ),
]


def sep(char="=", width=62):
    print(char * width)


def get_anchored_records(n: int, verified_ids: set) -> list:
    """Fetch N fully-anchored action/escalation records that passed baseline."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT d.record_id, d.record_type, d.decision, d.sha256_hex,
               d.canonical_json, b.merkle_root
        FROM decisions d
        JOIN batches b ON d.batch_id = b.id
        WHERE d.record_type IN ('action', 'escalation')
          AND b.merkle_root IS NOT NULL
        ORDER BY RANDOM()
        LIMIT ?
    """, (n * 4,)).fetchall()
    conn.close()
    rows = [dict(r) for r in rows if r["record_id"] in verified_ids]
    return rows[:n * 2]  # return a pool


def run_demo(n_tamper: int):
    sep()
    print(BOLD("  ATTEST — LIVE TAMPER-DETECTION DEMO"))
    print(DIM("  Proving that every AI decision is cryptographically sealed."))
    sep()
    time.sleep(0.5)

    # ── Phase 1: Baseline ──────────────────────────────────────────────────────
    print(f"\n{BOLD('[Phase 1]')} Running baseline verification on all records...\n")
    time.sleep(0.3)
    baseline = run_verification(output_json=False)
    time.sleep(0.3)

    verified_ids = {r["record_id"] for r in baseline if r["status"] == "VERIFIED"}
    n_total      = len(baseline)
    n_verified   = len(verified_ids)

    if n_verified == 0:
        print(RED("\n  ERROR: No verified records found."))
        print("    Run:  python demo/run_pipeline.py\n")
        sys.exit(1)

    print(f"\n  {GREEN('OK')} Baseline complete: "
          f"{GREEN(str(n_verified))}/{n_total} records {GREEN('VERIFIED')}. All clean.\n")
    time.sleep(0.8)

    # ── Phase 2: Silent corruption ─────────────────────────────────────────────
    sep("-")
    print(f"\n{BOLD('[Phase 2]')} Silently corrupting {n_tamper} records...")
    print(DIM("  (Simulating an attacker with direct database write access)\n"))
    time.sleep(0.6)

    pool = get_anchored_records(n_tamper, verified_ids)

    if not pool:
        print(RED("  ERROR: No tamperable anchored records. Run run_pipeline.py first."))
        sys.exit(1)

    # Choose diverse record types where possible
    seen_types = set()
    chosen = []
    for r in pool:
        key = r["record_type"] + (r.get("decision") or "")
        if key not in seen_types:
            chosen.append(r)
            seen_types.add(key)
        if len(chosen) == n_tamper:
            break
    for r in pool:
        if r not in chosen:
            chosen.append(r)
        if len(chosen) == n_tamper:
            break

    tampered_ids = []
    tamper_log   = []

    for i, record in enumerate(chosen):
        field, new_value, label = TAMPER_SCENARIOS[i % len(TAMPER_SCENARIOS)]
        try:
            # Guard against no-ops: verify the field value actually changes
            import json as _json
            current_canon = _json.loads(record["canonical_json"])
            keys = field.split(".")
            current_val = current_canon
            for k in keys:
                current_val = current_val.get(k, None)
                if current_val is None:
                    break
            if str(current_val) == str(new_value):
                # Same value — pick a different guaranteed-different value
                new_value = new_value + "__tampered"

            tamper_decision(record["record_id"], field, new_value)
            tampered_ids.append(record["record_id"])
            tamper_log.append({
                "record_id":   record["record_id"],
                "record_type": record["record_type"],
                "field":       field,
                "new_value":   new_value,
                "label":       label,
            })
            print(f"  {YELLOW('EDIT')}  {DIM(record['record_id'][:16]+'...')}")
            print(f"        Type:   {CYAN(record['record_type'])}")
            print(f"        Attack: {YELLOW(label)}")
            print(f"        Edit:   {field} -> {YELLOW(repr(new_value))}\n")
            time.sleep(0.4)
        except Exception as e:
            print(f"  {YELLOW('SKIP')}  {record['record_id'][:12]}...: {e}")

    if not tampered_ids:
        print(RED("  ERROR: No records could be tampered. Check DB schema."))
        sys.exit(1)

    print(f"  {len(tampered_ids)} records silently corrupted."
          f"  {DIM('The verifier has not been told anything.')}\n")
    time.sleep(1.0)

    # ── Phase 3: Re-verify ────────────────────────────────────────────────────
    sep("-")
    print(f"\n{BOLD('[Phase 3]')} Re-running full verifier...\n")
    time.sleep(0.5)

    post_results = run_verification(output_json=False)
    post_map     = {r["record_id"]: r for r in post_results}

    # ── Phase 4: Per-tamper breakdown ─────────────────────────────────────────
    sep()
    print(BOLD("  PER-RECORD DETECTION RESULTS"))
    sep("-")
    print()

    for entry in tamper_log:
        rid    = entry["record_id"]
        result = post_map.get(rid, {})
        status = result.get("status", "UNKNOWN")
        caught = status in ("HASH_MISMATCH", "PROOF_INVALID")

        icon = GREEN("CAUGHT") if caught else RED("MISSED")
        print(f"  [{icon}]  {DIM(rid[:16]+'...')}  [{CYAN(entry['record_type'])}]")
        print(f"           Attack:  {entry['label']}")
        print(f"           Status:  {RED(status) if not caught else GREEN(status)}")
        if result.get("error"):
            print(f"           Reason:  {DIM(result['error'])}")
        print()
        time.sleep(0.2)

    # ── Phase 5: Final scorecard ───────────────────────────────────────────────
    sep()
    print(BOLD("  TAMPER-DETECTION SCORECARD"))
    sep()

    detected  = sum(
        1 for r in post_results
        if r["status"] in ("HASH_MISMATCH", "PROOF_INVALID")
        and r["record_id"] in tampered_ids
    )
    false_pos = sum(
        1 for r in post_results
        if r["status"] not in ("VERIFIED", "NOT_ANCHORED", "CHAIN_ERROR")
        and r["record_id"] not in tampered_ids
    )
    clean_count    = len(post_results) - len(tampered_ids)
    detection_rate = (detected / len(tampered_ids) * 100) if tampered_ids else 0.0
    fp_rate        = (false_pos / max(1, clean_count)) * 100

    print(f"\n  Records total:             {n_total}")
    print(f"  Records tampered:          {len(tampered_ids)}")
    print()

    score_col = GREEN if detection_rate == 100.0 else RED
    fp_col    = GREEN if false_pos == 0 else YELLOW
    print(f"  Tampers detected:          {score_col(str(detected))} / {len(tampered_ids)}"
          f"   ({score_col(f'{detection_rate:.0f}%')})   <- target 100%")
    print(f"  False positives:           {fp_col(str(false_pos))}"
          f"   ({fp_col(f'{fp_rate:.1f}%')})   <- target   0%")
    print(f"  Clean records still valid: {clean_count - false_pos}")
    print()

    if detection_rate == 100.0 and false_pos == 0:
        sep()
        print(BOLD(GREEN("  PERFECT SCORE — Audit trail is tamper-proof.")))
        print(GREEN("  Every altered record was caught immediately."))
        print(GREEN("  Zero clean records flagged incorrectly."))
        sep()
    else:
        sep("-")
        print(YELLOW("  PARTIAL — some records not caught. Check results above."))
        sep("-")

    print(f"""
  {BOLD('How the detection works:')}
    1. Every AI decision is SHA-256 hashed the moment it is written.
    2. 10 hashes are batched into a Merkle tree; the root is stored on-chain.
    3. The verifier re-hashes canonical_json and compares to the sealed hash.
    4. Any byte change -> HASH_MISMATCH instantly, with no chain query needed.

  {BOLD('Note:')} Tampered records remain in db/attest.db (shown as FAIL in viewer).
  {DIM('       Reset: rm db/attest.db && python demo/run_pipeline.py')}
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Attest Live Tamper-Detection Demo (Phase 12)"
    )
    parser.add_argument(
        "--n", type=int, default=5,
        help="Number of records to corrupt (default: 5)"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Wipe database, load real Kaggle data, retrain models, then run demo"
    )
    parser.add_argument(
        "--csv", default=None,
        help="Path to your own CSV file to use instead of Kaggle data (used with --reset)"
    )
    parser.add_argument(
        "--synthetic", action="store_true",
        help="Use synthetic data instead of Kaggle (used with --reset)"
    )
    parser.add_argument(
        "--limit", type=int, default=500,
        help="Max transactions to process through the pipeline (default: 500)"
    )
    args = parser.parse_args()

    ROOT = Path(__file__).parent.parent

    if args.reset:
        # Step 1: Wipe the database
        db_path = ROOT / "db" / "attest.db"
        if db_path.exists():
            db_path.unlink()
            print(DIM("  [reset] Removed db/attest.db"))

        # Step 2: Load real / user / synthetic data
        loader = ROOT / "data" / "load_real_data.py"
        if args.csv:
            print(DIM(f"  [reset] Loading user CSV: {args.csv}"))
            data_cmd = [sys.executable, str(loader), "--csv", args.csv]
        elif args.synthetic:
            print(DIM("  [reset] Generating synthetic data..."))
            data_cmd = [sys.executable, str(loader), "--synthetic"]
        else:
            print(DIM("  [reset] Downloading real Kaggle data (mlg-ulb/creditcardfraud)..."))
            data_cmd = [sys.executable, str(loader), "--limit", "10000"]

        result = subprocess.run(data_cmd, cwd=ROOT)
        if result.returncode != 0:
            print(RED("  Data loading failed. See output above."))
            sys.exit(1)

        # Step 3: Retrain classifier
        print(DIM("\n  [reset] Training XGBoost classifier on real data..."))
        result = subprocess.run(
            [sys.executable, "ml/train_classifier.py"], cwd=ROOT
        )
        if result.returncode != 0:
            print(RED("  Classifier training failed."))
            sys.exit(1)

        # Step 4: Retrain anomaly detector
        print(DIM("\n  [reset] Training anomaly detector on real data..."))
        result = subprocess.run(
            [sys.executable, "ml/train_anomaly.py"], cwd=ROOT
        )
        if result.returncode != 0:
            print(RED("  Anomaly detector training failed."))
            sys.exit(1)

        # Step 5: Run pipeline
        print(DIM(f"\n  [reset] Running pipeline (--limit {args.limit})...\n"))
        result = subprocess.run(
            [sys.executable, "demo/run_pipeline.py", "--limit", str(args.limit)],
            cwd=ROOT,
        )
        if result.returncode != 0:
            print(RED("  Pipeline failed. See output above."))
            sys.exit(1)
        print()

    run_demo(n_tamper=args.n)
