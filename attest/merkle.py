"""
attest/merkle.py

Builds a Merkle tree from a list of hex-string SHA-256 leaf hashes.
Batch size: 10. Partial batches right-padded with ZERO_HASH.

Internal node hash: sha256(left_bytes + right_bytes)
"""

import hashlib
import math

ZERO_HASH = "0" * 64  # 32 zero bytes as hex
BATCH_SIZE = 10


def _combine(left: str, right: str) -> str:
    """SHA-256(left_bytes + right_bytes) → hex string."""
    data = bytes.fromhex(left) + bytes.fromhex(right)
    return hashlib.sha256(data).hexdigest()


def _next_power_of_two(n: int) -> int:
    if n <= 1:
        return 1
    return 2 ** math.ceil(math.log2(n))


def build_merkle_tree(leaf_hashes: list) -> dict:
    """
    Args:
        leaf_hashes: list of hex SHA-256 strings (length <= BATCH_SIZE)
    Returns:
        {
            "root": str,
            "leaves": list[str],        # padded leaves
            "tree": list[list[str]],    # full tree, bottom-up
            "proofs": list[list[dict]], # proof path per original leaf
        }
    """
    if not leaf_hashes:
        raise ValueError("Cannot build Merkle tree from empty list")

    # Pad to next power of 2
    padded_size = _next_power_of_two(len(leaf_hashes))
    leaves = leaf_hashes + [ZERO_HASH] * (padded_size - len(leaf_hashes))

    # Build tree bottom-up
    tree = [leaves]
    current = leaves
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            next_level.append(_combine(current[i], current[i + 1]))
        tree.append(next_level)
        current = next_level

    root = tree[-1][0]

    # Build proof paths for each original (non-padded) leaf
    proofs = []
    for leaf_idx in range(len(leaf_hashes)):
        proof = []
        idx = leaf_idx
        for level_nodes in tree[:-1]:  # exclude root level
            sibling_idx = idx ^ 1      # XOR with 1 gives sibling index
            direction = "right" if idx % 2 == 0 else "left"
            proof.append({
                "sibling": level_nodes[sibling_idx],
                "direction": direction,
            })
            idx //= 2
        proofs.append(proof)

    return {
        "root": root,
        "leaves": leaves,
        "tree": tree,
        "proofs": proofs,
    }


def verify_proof(leaf_hash: str, proof: list, expected_root: str) -> bool:
    """
    Verify a single leaf's Merkle proof against the expected root.
    proof: list of {"sibling": hex, "direction": "left"|"right"}
    """
    current = leaf_hash
    for step in proof:
        sibling = step["sibling"]
        direction = step["direction"]
        if direction == "right":
            current = _combine(current, sibling)
        else:
            current = _combine(sibling, current)
    return current == expected_root
