"""
demo/run_pipeline.py

Runs the complete Attest pipeline on the synthetic dataset:
  Step 0: Hash + anchor the policy file
  Step 1: Load synthetic transactions from data/transactions.json
  Step 2: For each transaction, call decide_recovery_action()
          (@audited_action handles hashing + batching + anchoring)
  Step 3: Force-flush any remaining unbatched decisions (partial batch)
  Step 4: Print summary statistics

Run: python demo/run_pipeline.py
"""

import sys
import json
import uuid
import argparse
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from attest.storage import (
    init_db, insert_decision, get_unbatched_decisions,
    insert_batch, update_batch_assignment, insert_anchor, get_connection,
)
from attest.hasher import hash_file, canonical_json, sha256_hex, now_iso, AGENT_VERSION
from attest.merkle import build_merkle_tree, BATCH_SIZE
from attest.chain import anchor_root
from attest.agent import decide_recovery_action

POLICY_PATH = Path(__file__).parent.parent / "policy.yaml"
DATA_PATH   = Path(__file__).parent.parent / "data" / "transactions.json"


def anchor_policy():
    """Step 0: Hash the policy file and store as a policy_anchor record."""
    print("\n[Step 0] Anchoring policy file...")
    policy_hash = hash_file(str(POLICY_PATH))

    with open(POLICY_PATH) as f:
        policy = yaml.safe_load(f)

    record = {
        "agent_version": AGENT_VERSION,
        "bounds_applied": {},
        "confidence": 1.0,
        "decision": "policy_anchor",
        "input_context": {"policy_path": str(POLICY_PATH)},
        "policy_check": "ALLOWED",
        "policy_content_hash": policy_hash,
        "policy_version": policy.get("version", "unknown"),
        "record_type": "policy_anchor",
        "timestamp": now_iso(),
        "transaction_id": None,
    }
    canonical = canonical_json(record)
    digest = sha256_hex(canonical)
    record_id = str(uuid.uuid4())

    init_db()
    insert_decision(
        record_id=record_id,
        record_type="policy_anchor",
        transaction_id=None,
        canonical_json=canonical,
        sha256_hex=digest,
        decision="policy_anchor",
        confidence=1.0,
        policy_check="ALLOWED",
        timestamp=record["timestamp"],
    )
    print(f"  Policy file hash: {policy_hash[:20]}...")
    print(f"  Record ID:        {record_id}")
    print(f"  Policy version:   {policy.get('version')}")


def flush_partial_batch():
    """Force-flush any remaining unbatched decisions as a partial final batch."""
    rows = get_unbatched_decisions(limit=BATCH_SIZE)
    if not rows:
        return

    print(f"\n[Flush] Processing partial batch of {len(rows)} decisions...")
    leaf_hashes = [row["sha256_hex"] for row in rows]
    record_ids  = [row["record_id"]  for row in rows]

    tree_data = build_merkle_tree(leaf_hashes)
    merkle_root = tree_data["root"]
    proofs = tree_data["proofs"]

    conn = get_connection()
    seq = (conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0] or 0) + 1
    conn.close()

    batch_id = insert_batch(seq, merkle_root, len(leaf_hashes), record_ids)
    update_batch_assignment(record_ids, batch_id, proofs)

    try:
        tx_hash, block_number, chain_id = anchor_root(merkle_root, batch_id)
        insert_anchor(batch_id, merkle_root, tx_hash, block_number, chain_id, now_iso())
        print(f"  ✅ Anchored batch {seq}. Root={merkle_root[:12]}... TX={tx_hash[:12]}...")
    except Exception as e:
        print(f"  ⚠️  Anchoring skipped: {e}")


def main():
    parser = argparse.ArgumentParser(description="Attest end-to-end pipeline")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Process only the first N transactions (default: all)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ATTEST — End-to-End Pipeline")
    print("=" * 60)

    anchor_policy()

    print(f"\n[Step 1] Loading transactions from {DATA_PATH}...")
    if not DATA_PATH.exists():
        print("ERROR: Run 'python data/generate_synthetic.py' first.")
        sys.exit(1)

    with open(DATA_PATH) as f:
        transactions = json.load(f)

    if args.limit:
        transactions = transactions[:args.limit]
        print(f"  Loaded {len(transactions)} transactions (limit={args.limit}).")
    else:
        print(f"  Loaded {len(transactions)} transactions.")

    print("\n[Step 2] Processing decisions...")
    results = []
    escalations = anomalies = blocked = 0

    for i, txn in enumerate(transactions):
        result = decide_recovery_action(txn)
        results.append(result)

        if result.get("is_escalation"):              escalations += 1
        if result.get("is_anomaly"):                 anomalies   += 1
        if result.get("policy_check") == "BLOCKED":  blocked     += 1

        if (i + 1) % 50 == 0 or (i + 1) == len(transactions):
            print(f"  Processed {i+1}/{len(transactions)}...")

    flush_partial_batch()

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE — Summary")
    print("=" * 60)
    print(f"  Total decisions:   {len(results)}")
    print(f"  Escalations:       {escalations}")
    print(f"  Policy-blocked:    {blocked}")
    print(f"  Anomaly-flagged:   {anomalies}")
    print(f"  Action breakdown:  {dict(Counter(r.get('action') for r in results))}")

    conn = get_connection()
    batch_count  = conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
    anchor_count = conn.execute("SELECT COUNT(*) FROM anchors").fetchone()[0]
    conn.close()

    print(f"\n  Merkle batches created:  {batch_count}")
    print(f"  On-chain anchors:        {anchor_count}")
    if anchor_count > 0:
        reduction = (1 - anchor_count / max(len(results), 1)) * 100
        print(f"  On-chain TX reduction:   {reduction:.0f}%")
    print(f"\nDatabase: db/attest.db")
    print("Run 'python verifier/verify.py --all' to verify all records.")


if __name__ == "__main__":
    main()
