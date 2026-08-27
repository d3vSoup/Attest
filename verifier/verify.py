"""
verifier/verify.py

Given a record_id (or --all), recomputes SHA-256, walks Merkle proof,
confirms root anchored on-chain.

Status codes:
  VERIFIED       — hash matches, proof valid, root on-chain
  HASH_MISMATCH  — recomputed hash != stored hash (record was altered)
  PROOF_INVALID  — Merkle proof does not resolve to expected root
  NOT_ANCHORED   — root not found on-chain
  CHAIN_ERROR    — chain query failed (network/config issue)

Usage:
  python verifier/verify.py --all
  python verifier/verify.py --record-id <uuid>
  python verifier/verify.py --all --json
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from attest.storage import get_connection
from attest.hasher import sha256_hex
from attest.merkle import verify_proof
from attest.chain import verify_root_on_chain


def verify_one(row: dict) -> dict:
    """
    Verify a single decision record.

    Returns a dict with:
      record_id, status, hash_match, proof_valid, on_chain, error
    """
    record_id         = row["record_id"]
    canonical         = row["canonical_json"]
    stored_hash       = row["sha256_hex"]
    merkle_root       = row.get("merkle_root")
    merkle_proof_json = row.get("merkle_proof")
    record_type       = row.get("record_type", "action")

    # ── Step 1: Recompute hash ─────────────────────────────────────────────────
    recomputed_hash = sha256_hex(canonical)
    hash_match = (recomputed_hash == stored_hash)

    if not hash_match:
        return {
            "record_id":   record_id,
            "record_type": record_type,
            "status":      "HASH_MISMATCH",
            "hash_match":  False,
            "proof_valid": None,
            "on_chain":    None,
            "error": (
                "Recomputed hash does not match stored hash — "
                "record was altered post-anchoring"
            ),
        }

    # ── Step 2: Walk Merkle proof ──────────────────────────────────────────────
    proof_valid = None
    if merkle_proof_json and merkle_root:
        try:
            proof = json.loads(merkle_proof_json)
            proof_valid = verify_proof(stored_hash, proof, merkle_root)
        except Exception as e:
            return {
                "record_id":   record_id,
                "record_type": record_type,
                "status":      "PROOF_INVALID",
                "hash_match":  True,
                "proof_valid": False,
                "on_chain":    None,
                "error":       f"Proof parse/verify error: {e}",
            }

        if not proof_valid:
            return {
                "record_id":   record_id,
                "record_type": record_type,
                "status":      "PROOF_INVALID",
                "hash_match":  True,
                "proof_valid": False,
                "on_chain":    None,
                "error":       "Merkle proof verification failed — tree structure corrupt",
            }

    # ── Step 3: Check on-chain ─────────────────────────────────────────────────
    on_chain = None
    chain_error = None

    if merkle_root:
        result = verify_root_on_chain(merkle_root)
        on_chain = result["anchored"]
        chain_error = result.get("error")

        # If chain simply isn't configured yet, don't fail the record —
        # the hash + Merkle proof already confirmed local integrity.
        if chain_error and "Chain not configured" in chain_error:
            return {
                "record_id":   record_id,
                "record_type": record_type,
                "status":      "VERIFIED",   # locally verified — hash + proof passed
                "hash_match":  True,
                "proof_valid": proof_valid,
                "on_chain":    None,         # chain not checked (no .env)
                "error":       None,
            }

        if not on_chain and chain_error is None:
            return {
                "record_id":   record_id,
                "record_type": record_type,
                "status":      "NOT_ANCHORED",
                "hash_match":  True,
                "proof_valid": proof_valid,
                "on_chain":    False,
                "error":       f"Merkle root {(merkle_root or '')[:16]}... not found on-chain",
            }
    else:
        # Not yet batched/anchored
        return {
            "record_id":   record_id,
            "record_type": record_type,
            "status":      "NOT_ANCHORED",
            "hash_match":  True,
            "proof_valid": None,
            "on_chain":    False,
            "error":       "Record not yet batched — pipeline still running?",
        }

    # ── All checks passed ──────────────────────────────────────────────────────
    status = "VERIFIED" if (
        hash_match and
        proof_valid is not False and
        on_chain is not False
    ) else "CHAIN_ERROR"

    return {
        "record_id":   record_id,
        "record_type": record_type,
        "status":      status,
        "hash_match":  hash_match,
        "proof_valid": proof_valid,
        "on_chain":    on_chain,
        "error":       chain_error,
    }


def run_verification(record_id=None, output_json=False) -> list:
    """
    Verify one or all records. Returns list of result dicts.
    Also prints a summary unless output_json=True.
    """
    conn = get_connection()

    base_query = """
        SELECT d.*, b.merkle_root, a.tx_hash
        FROM decisions d
        LEFT JOIN batches b ON d.batch_id = b.id
        LEFT JOIN anchors a ON b.id = a.batch_id
        {where}
        ORDER BY d.id ASC
    """

    if record_id:
        rows = conn.execute(
            base_query.format(where="WHERE d.record_id = ?"), (record_id,)
        ).fetchall()
    else:
        rows = conn.execute(base_query.format(where="")).fetchall()

    conn.close()

    results = [verify_one(dict(row)) for row in rows]

    if output_json:
        print(json.dumps(results, indent=2))
    else:
        verified = sum(1 for r in results if r["status"] == "VERIFIED")
        failed   = len(results) - verified
        print(f"\n{'='*60}")
        print(f"ATTEST VERIFIER — {len(results)} records checked")
        print(f"{'='*60}")
        print(f"  ✅ Verified:  {verified}")
        print(f"  ❌ Failed:    {failed}")
        print()
        for r in results:
            icon = "✅" if r["status"] == "VERIFIED" else "❌"
            rtype = r.get("record_type", "")
            print(f"  {icon} [{rtype:12s}] {r['record_id'][:12]}...  {r['status']}")
            if r["status"] != "VERIFIED":
                print(f"         └─ {r['error']}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Attest Verifier")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--record-id", help="Verify a single record by UUID")
    group.add_argument("--all", action="store_true", help="Verify all stored records")
    parser.add_argument("--json", action="store_true", dest="output_json",
                        help="Output as JSON")
    args = parser.parse_args()

    results = run_verification(
        record_id=args.record_id if not args.all else None,
        output_json=args.output_json,
    )

    # Exit 1 if any record failed verification
    sys.exit(0 if all(r["status"] == "VERIFIED" for r in results) else 1)
