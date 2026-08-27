"""
attest/hasher.py

Canonical JSON serialization and SHA-256 hashing.
INVARIANT: sort_keys=True, separators=(',', ':'), no extra whitespace.
Any deviation makes hashes non-reproducible across machines/Python versions.
"""

import hashlib
import json
from datetime import datetime, timezone

AGENT_VERSION = "attest-v1.0"


def canonical_json(record: dict) -> str:
    """
    Serialize a dict to canonical JSON.
    - Keys sorted alphabetically (recursive)
    - No spaces after separators
    - UTF-8 safe
    Must produce identical output for identical content on any machine.
    """
    return json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def sha256_hex(data) -> str:
    """Return lowercase hex SHA-256 digest of string or bytes."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def hash_record(record: dict) -> tuple:
    """
    Returns (canonical_json_str, sha256_hex_str).
    canonical string is stored locally.
    hex digest is batched into the Merkle tree.
    """
    canonical = canonical_json(record)
    digest = sha256_hex(canonical)
    return canonical, digest


def hash_file(filepath: str) -> str:
    """SHA-256 of raw file bytes — used for policy.yaml anchoring."""
    with open(filepath, "rb") as f:
        return sha256_hex(f.read())


def now_iso() -> str:
    """Current UTC time in ISO 8601 with microseconds."""
    return datetime.now(timezone.utc).isoformat()


def build_action_record(
    transaction_id,
    input_context: dict,
    decision: str,
    confidence: float,
    policy_check: str,
    policy_version: str,
    bounds_applied: dict,
    record_type: str = "action",
    explainability: dict = None,
) -> dict:
    """
    Build a canonical decision record. All fields always present
    so hashes are stable across Python sessions.
    """
    return {
        "agent_version": AGENT_VERSION,
        "bounds_applied": bounds_applied,
        "confidence": round(float(confidence), 6),
        "decision": decision,
        "input_context": input_context,
        "policy_check": policy_check,
        "policy_version": policy_version,
        "record_type": record_type,
        "timestamp": now_iso(),
        "transaction_id": transaction_id,
        "explainability": explainability or {},
    }
