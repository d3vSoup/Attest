"""
attest/chain.py

Anchors a Merkle root to the deployed Attest contract on Polygon Amoy.
If environment variables are not set, anchoring raises RuntimeError
(caller in wrapper.py catches + logs but continues locally).

Required env vars (in .env):
  PRIVATE_KEY        — deployer wallet private key (0x...)
  RPC_URL            — e.g., https://rpc-amoy.polygon.technology
  CONTRACT_ADDRESS   — deployed contract address (0x...)
  CHAIN_ID           — 80002 for Polygon Amoy
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "root",    "type": "bytes32"},
            {"internalType": "uint256", "name": "batchId", "type": "uint256"},
        ],
        "name": "logRoot",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "root", "type": "bytes32"}],
        "name": "isAnchored",
        "outputs": [
            {"internalType": "bool",    "name": "anchored",  "type": "bool"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "root",      "type": "bytes32"},
            {"indexed": False, "name": "timestamp",  "type": "uint256"},
            {"indexed": True,  "name": "sender",     "type": "address"},
            {"indexed": False, "name": "batchId",    "type": "uint256"},
        ],
        "name": "Anchored",
        "type": "event",
    },
]


def _get_web3():
    """Return a connected Web3 instance or None if not configured."""
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        return None
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            print("[chain.py] WARNING: Could not connect to RPC. Anchoring disabled.")
            return None
        return w3
    except Exception as e:
        print(f"[chain.py] Web3 init failed: {e}")
        return None


def anchor_root(merkle_root_hex: str, batch_id: int) -> tuple:
    """
    Anchor the Merkle root on-chain.

    Args:
        merkle_root_hex: 64-char hex string (SHA-256 Merkle root)
        batch_id:        local DB batch id

    Returns:
        (tx_hash_hex, block_number, chain_id)

    Raises:
        RuntimeError if chain is not configured (caller should catch + skip)
    """
    w3 = _get_web3()
    if w3 is None:
        raise RuntimeError(
            "Chain not configured — set RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS in .env"
        )

    private_key = os.getenv("PRIVATE_KEY")
    contract_address = os.getenv("CONTRACT_ADDRESS")
    chain_id = int(os.getenv("CHAIN_ID", "80002"))

    if not all([private_key, contract_address]):
        raise RuntimeError("PRIVATE_KEY or CONTRACT_ADDRESS not set in .env")

    from web3 import Web3

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=CONTRACT_ABI,
    )
    account = w3.eth.account.from_key(private_key)

    # Convert 64-char hex to bytes32
    root_bytes = bytes.fromhex(merkle_root_hex)
    if len(root_bytes) != 32:
        raise ValueError(f"Merkle root must be 32 bytes, got {len(root_bytes)}")

    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    txn = contract.functions.logRoot(root_bytes, batch_id).build_transaction({
        "chainId": chain_id,
        "from": account.address,
        "nonce": nonce,
        "gas": 80000,
        "gasPrice": int(gas_price * 1.2),  # 20% buffer
    })

    signed = w3.eth.account.sign_transaction(txn, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)  # web3.py v7 API
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt.status != 1:
        raise RuntimeError(f"Transaction reverted. Hash: {tx_hash.hex()}")

    return tx_hash.hex(), receipt.blockNumber, chain_id


def verify_root_on_chain(merkle_root_hex: str) -> dict:
    """
    Query the contract to check if a root is anchored.
    Returns {"anchored": bool, "timestamp": int|None, "error": str|None}
    """
    w3 = _get_web3()
    if w3 is None:
        return {"anchored": False, "timestamp": None, "error": "Chain not configured"}

    contract_address = os.getenv("CONTRACT_ADDRESS")
    if not contract_address:
        return {"anchored": False, "timestamp": None, "error": "CONTRACT_ADDRESS not set"}

    from web3 import Web3
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=CONTRACT_ABI,
    )

    try:
        root_bytes = bytes.fromhex(merkle_root_hex)
        anchored, timestamp = contract.functions.isAnchored(root_bytes).call()
        return {
            "anchored": anchored,
            "timestamp": int(timestamp) if anchored else None,
            "error": None,
        }
    except Exception as e:
        return {"anchored": False, "timestamp": None, "error": str(e)}
