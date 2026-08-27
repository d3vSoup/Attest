"""
attest/storage.py

All SQLite read/write for Attest. The database is the local source of truth.
Nothing from here goes on-chain except sha256_hex values.

Tables:
  decisions  — one row per hashed decision/escalation/policy_anchor
  batches    — one row per Merkle batch (10 decisions → 1 root)
  anchors    — one row per on-chain anchor (batch_id → tx_hash)
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "attest.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # safe concurrent reads
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS decisions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id        TEXT    NOT NULL UNIQUE,
            record_type      TEXT    NOT NULL,
            transaction_id   TEXT    UNIQUE,
            canonical_json   TEXT    NOT NULL,
            sha256_hex       TEXT    NOT NULL,
            decision         TEXT,
            confidence       REAL,
            policy_check     TEXT,
            timestamp        TEXT    NOT NULL,
            batch_id         INTEGER,
            leaf_index       INTEGER,
            merkle_proof     TEXT,
            is_anomaly       INTEGER DEFAULT 0,
            created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS batches (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_seq        INTEGER NOT NULL UNIQUE,
            merkle_root      TEXT    NOT NULL,
            leaf_count       INTEGER NOT NULL,
            decision_ids     TEXT    NOT NULL,
            anchored         INTEGER DEFAULT 0,
            created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS anchors (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id         INTEGER NOT NULL,
            merkle_root      TEXT    NOT NULL,
            tx_hash          TEXT,
            block_number     INTEGER,
            chain_id         INTEGER,
            anchored_at      TEXT,
            created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(batch_id) REFERENCES batches(id)
        );

        CREATE INDEX IF NOT EXISTS idx_decisions_sha256 ON decisions(sha256_hex);
        CREATE INDEX IF NOT EXISTS idx_decisions_batch  ON decisions(batch_id);
        CREATE INDEX IF NOT EXISTS idx_batches_root     ON batches(merkle_root);
    """)
    conn.commit()
    conn.close()


def insert_decision(
    record_id: str,
    record_type: str,
    transaction_id,
    canonical_json: str,
    sha256_hex: str,
    decision,
    confidence,
    policy_check,
    timestamp: str,
    is_anomaly: bool = False,
) -> int:
    """Insert a hashed decision. Returns the row id."""
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO decisions
          (record_id, record_type, transaction_id, canonical_json, sha256_hex,
           decision, confidence, policy_check, timestamp, is_anomaly)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (record_id, record_type, transaction_id, canonical_json, sha256_hex,
          decision, confidence, policy_check, timestamp, int(is_anomaly)))
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_unbatched_decisions(limit: int = 10) -> list:
    """Fetch up to `limit` decisions that haven't been batched yet."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM decisions
        WHERE batch_id IS NULL AND record_type != 'policy_anchor'
        ORDER BY id ASC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def update_batch_assignment(record_ids: list, batch_id: int, proofs: list):
    """Assign decisions to a batch and store their Merkle proof paths."""
    conn = get_connection()
    for i, (record_id, proof) in enumerate(zip(record_ids, proofs)):
        conn.execute("""
            UPDATE decisions SET batch_id=?, leaf_index=?, merkle_proof=?
            WHERE record_id=?
        """, (batch_id, i, json.dumps(proof), record_id))
    conn.commit()
    conn.close()


def insert_batch(batch_seq: int, merkle_root: str, leaf_count: int, decision_ids: list) -> int:
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO batches (batch_seq, merkle_root, leaf_count, decision_ids)
        VALUES (?,?,?,?)
    """, (batch_seq, merkle_root, leaf_count, json.dumps(decision_ids)))
    batch_id = cur.lastrowid
    conn.commit()
    conn.close()
    return batch_id


def insert_anchor(batch_id: int, merkle_root: str, tx_hash: str, block_number: int, chain_id: int, anchored_at: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO anchors (batch_id, merkle_root, tx_hash, block_number, chain_id, anchored_at)
        VALUES (?,?,?,?,?,?)
    """, (batch_id, merkle_root, tx_hash, block_number, chain_id, anchored_at))
    conn.execute("UPDATE batches SET anchored=1 WHERE id=?", (batch_id,))
    conn.commit()
    conn.close()


def get_all_decisions_for_viewer() -> list:
    """Return all decisions joined with batch/anchor data for the Streamlit viewer."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT d.*, b.merkle_root, b.batch_seq, a.tx_hash, a.block_number
        FROM decisions d
        LEFT JOIN batches b ON d.batch_id = b.id
        LEFT JOIN anchors a ON b.id = a.batch_id
        ORDER BY d.id ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def tamper_decision(record_id: str, field: str, new_value: str):
    """
    Silently edit a stored canonical_json to simulate a tampered record.
    Used ONLY by the tamper demo. In real life this represents an attacker
    editing the database directly.
    field supports dot notation: "bounds_applied.max_discount_pct"
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT canonical_json FROM decisions WHERE record_id=?", (record_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"Record {record_id} not found")
    record = json.loads(row["canonical_json"])
    keys = field.split(".")
    target = record
    for k in keys[:-1]:
        target = target[k]
    target[keys[-1]] = new_value
    new_canonical = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    conn.execute(
        "UPDATE decisions SET canonical_json=? WHERE record_id=?",
        (new_canonical, record_id)
    )
    conn.commit()
    conn.close()
