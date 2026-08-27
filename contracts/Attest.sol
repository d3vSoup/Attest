// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Attest
 * @notice Tamper-evident on-chain anchor for AI agent decision Merkle roots.
 *         No value is stored or transferred. This contract is a public
 *         bulletin board for SHA-256 hashes only.
 *
 * @dev Deploy to Polygon Amoy (chainId 80002) or Base Sepolia (chainId 84532).
 *
 *      ONE function: logRoot(bytes32 root, uint256 batchId)
 *      ONE event:    Anchored(bytes32 indexed root, uint256 timestamp,
 *                             address indexed sender, uint256 batchId)
 *
 *      Verification: query anchorTimestamps[root] or filter Anchored events
 *      via any public RPC / block explorer. If the root exists, it was
 *      published at that block timestamp and cannot be altered retroactively.
 *
 * Deployment steps (Remix IDE):
 *   1. Compiler: 0.8.19, optimization enabled (200 runs)
 *   2. Deploy & Run → Injected Provider (MetaMask)
 *   3. Network: Polygon Amoy (chainId 80002)
 *   4. Faucet: https://faucet.polygon.technology
 *   5. Copy deployed address → .env CONTRACT_ADDRESS
 */
contract Attest {

    // ── Events ─────────────────────────────────────────────────────────────────

    event Anchored(
        bytes32 indexed root,
        uint256 timestamp,
        address indexed sender,
        uint256 batchId
    );

    // ── State ──────────────────────────────────────────────────────────────────

    address public immutable owner;
    uint256 public totalAnchors;

    /// @notice Maps a Merkle root to the block.timestamp when it was first anchored.
    ///         0 means the root has never been anchored.
    mapping(bytes32 => uint256) public anchorTimestamps;

    // ── Constructor ────────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ── Core Function ──────────────────────────────────────────────────────────

    /**
     * @notice Anchor a Merkle root on-chain.
     * @param root    SHA-256 Merkle root (32 bytes).
     * @param batchId Local batch sequence number (for off-chain DB correlation).
     *
     * @dev Idempotent: anchoring the same root twice is harmless — the timestamp
     *      and totalAnchors counter are only updated on the first anchoring.
     *      The Anchored event is always emitted (useful for indexing repeat calls).
     */
    function logRoot(bytes32 root, uint256 batchId) external {
        require(root != bytes32(0), "Attest: zero root rejected");

        if (anchorTimestamps[root] == 0) {
            anchorTimestamps[root] = block.timestamp;
            totalAnchors++;
        }

        emit Anchored(root, block.timestamp, msg.sender, batchId);
    }

    // ── View Functions ─────────────────────────────────────────────────────────

    /**
     * @notice Check whether a given Merkle root has been anchored.
     * @param root The root to check.
     * @return anchored   True if the root was ever logged via logRoot().
     * @return timestamp  The block.timestamp of the first anchoring (0 if never anchored).
     */
    function isAnchored(bytes32 root)
        external
        view
        returns (bool anchored, uint256 timestamp)
    {
        timestamp = anchorTimestamps[root];
        anchored  = (timestamp != 0);
    }
}
