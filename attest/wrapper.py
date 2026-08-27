"""
attest/wrapper.py

The @audited_action decorator. Wraps any decision function and:
  1. Calls the underlying function to get the raw decision
  2. Checks the decision against policy bounds
  3. Builds the canonical record
  4. Hashes it and stores to SQLite
  5. Runs anomaly detector on the decision vector
  6. If 10 decisions accumulated, batches → Merkle tree → anchors on-chain
  7. Returns augmented result dict

Usage:
  @audited_action(policy_path="policy.yaml")
  def decide_recovery_action(transaction: dict) -> dict:
      return {"action": "retry", "discount_pct": 0.0, "confidence": 0.87}
"""

import uuid
import yaml
import joblib
import numpy as np
from functools import wraps
from pathlib import Path

from .hasher import build_action_record, hash_record, now_iso
from .storage import (
    init_db, insert_decision, get_unbatched_decisions,
    update_batch_assignment, insert_batch, insert_anchor, get_connection,
)
from .merkle import build_merkle_tree, BATCH_SIZE
from .chain import anchor_root

POLICY_PATH = Path(__file__).parent.parent / "policy.yaml"
ANOMALY_MODEL_PATH = Path(__file__).parent.parent / "models" / "anomaly_detector.pkl"

_policy_cache = None
_anomaly_model = None


def _load_policy(policy_path) -> dict:
    global _policy_cache
    if _policy_cache is None:
        with open(policy_path, "r") as f:
            _policy_cache = yaml.safe_load(f)
    return _policy_cache


def _load_anomaly_model():
    global _anomaly_model
    if _anomaly_model is None and ANOMALY_MODEL_PATH.exists():
        _anomaly_model = joblib.load(str(ANOMALY_MODEL_PATH))
    return _anomaly_model


def _check_policy(decision_result: dict, policy: dict) -> tuple:
    """Returns (policy_check: str, bounds_applied: dict, is_escalation: bool)"""
    bounds = policy["bounds"]
    action = decision_result.get("action", "")
    discount_pct = decision_result.get("discount_pct", 0.0)
    confidence = decision_result.get("confidence", 0.0)

    violations = []
    if action not in bounds["allowed_actions"]:
        violations.append(f"action '{action}' not in allowed_actions")
    if discount_pct > bounds["max_discount_pct"]:
        violations.append(f"discount_pct {discount_pct} > max {bounds['max_discount_pct']}")
    if confidence < bounds["escalation_confidence_threshold"] and action != "escalate":
        violations.append(
            f"confidence {confidence:.2f} < threshold {bounds['escalation_confidence_threshold']}"
        )

    policy_check = "BLOCKED" if violations else "ALLOWED"
    is_escalation = action == "escalate" or policy_check == "BLOCKED"

    bounds_applied = {
        "escalation_confidence_threshold": bounds["escalation_confidence_threshold"],
        "max_discount_pct": bounds["max_discount_pct"],
        "max_retries": bounds["max_retries"],
        "violations": violations,
    }
    return policy_check, bounds_applied, is_escalation


def _score_anomaly(decision_result: dict, input_context: dict) -> bool:
    """Returns True if the decision vector is flagged as anomalous."""
    # Hard rule: discount_pct > 15% always anomalous (policy max is 10%)
    discount_pct = float(decision_result.get("discount_pct", 0.0))
    if discount_pct > 15.0:
        return True

    model = _load_anomaly_model()
    if model is None:
        return False

    import math
    ACTION_MAP = {"retry": 0, "discount": 1, "alt_payment_nudge": 2, "escalate": 3}
    CHANNEL_MAP = {"upi": 0, "card": 1, "netbanking": 2, "wallet": 3}

    vec = np.array([[
        ACTION_MAP.get(decision_result.get("action", "escalate"), 3),
        float(decision_result.get("discount_pct", 0.0)),
        float(decision_result.get("confidence", 0.0)),
        float(input_context.get("retry_count_so_far", 0)),
        math.log1p(float(input_context.get("amount", 0))),
        int(decision_result.get("action") == "escalate"),
        int(input_context.get("hour_of_day", 12)),
        int(input_context.get("is_weekend", False)),
        CHANNEL_MAP.get(input_context.get("channel", "upi"), 0),
    ]])
    prediction = model.predict(vec)
    return bool(prediction[0] == -1)


def _maybe_batch_and_anchor():
    """Check if 10 unbatched decisions exist. If so, build Merkle tree and anchor."""
    rows = get_unbatched_decisions(limit=BATCH_SIZE)
    if len(rows) < BATCH_SIZE:
        return  # not enough yet

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
        print(f"[Attest] Batch {seq} anchored. Root={merkle_root[:12]}... TX={tx_hash[:12]}...")
    except Exception as e:
        print(f"[Attest] Anchoring skipped (chain not configured): {e}")


def audited_action(policy_path=POLICY_PATH):
    """
    Decorator factory.

    @audited_action(policy_path="policy.yaml")
    def my_decision_fn(transaction: dict) -> dict:
        return {"action": "retry", "discount_pct": 0.0, "confidence": 0.87}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(transaction: dict, *args, **kwargs):
            init_db()
            policy = _load_policy(policy_path)

            # 1. Get the raw decision
            decision_result = func(transaction, *args, **kwargs)

            # 2. Policy check
            policy_check, bounds_applied, is_escalation = _check_policy(decision_result, policy)

            # 3. If blocked, override action to "escalate"
            if policy_check == "BLOCKED":
                decision_result["action"] = "escalate"
                is_escalation = True

            # 4. Anomaly check
            is_anomaly = _score_anomaly(decision_result, transaction)

            # 5. Build record
            record_type = "escalation" if is_escalation else "action"
            record_id = str(uuid.uuid4())
            record = build_action_record(
                transaction_id=transaction.get("transaction_id", record_id),
                input_context={k: v for k, v in transaction.items() if k != "transaction_id"},
                decision=decision_result.get("action"),
                confidence=decision_result.get("confidence", 0.0),
                policy_check=policy_check,
                policy_version=policy.get("version", "unknown"),
                bounds_applied=bounds_applied,
                record_type=record_type,
                explainability=decision_result.get("explainability", {}),
            )

            # 6. Hash
            canonical, sha256 = hash_record(record)

            # 7. Store
            insert_decision(
                record_id=record_id,
                record_type=record_type,
                transaction_id=transaction.get("transaction_id"),
                canonical_json=canonical,
                sha256_hex=sha256,
                decision=decision_result.get("action"),
                confidence=decision_result.get("confidence", 0.0),
                policy_check=policy_check,
                timestamp=record["timestamp"],
                is_anomaly=is_anomaly,
            )

            # 8. Maybe batch + anchor
            _maybe_batch_and_anchor()

            # 9. Return augmented result
            decision_result["record_id"] = record_id
            decision_result["policy_check"] = policy_check
            decision_result["is_anomaly"] = is_anomaly
            decision_result["is_escalation"] = is_escalation
            return decision_result

        return wrapper
    return decorator
