// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BizNodeRegistry
 * @notice On-chain identity anchor, DNS binding, verification payments,
 *         and staking for the 1bz BizNode network on Polygon.
 *
 * Architecture:
 *   - On-chain: node identity, wallet binding, 1bz DNS alias, verified flag, stake
 *   - Off-chain: trust score, business documents, AI metadata (handled by FastAPI registry)
 *
 * Upgrade path:
 *   - transferOwnership() to a DAO contract when governance is ready
 */
contract BizNodeRegistry {

    // ── Data structures ───────────────────────────────────────────────────────

    struct Node {
        address wallet;          // Polygon wallet address of the node owner
        string  dnsName;         // 1bz alias, e.g. "shashi.1bz"
        bool    verified;        // True after verification payment
        uint256 stakeAmount;     // Total MATIC staked (wei)
        uint256 registeredAt;    // Block timestamp of registration
        bool    active;          // False if node has been deregistered
    }

    // ── Storage ───────────────────────────────────────────────────────────────

    /// nodeHash (keccak256 of node_id string) → Node
    mapping(bytes32 => Node) public nodes;

    /// dnsName → nodeHash (for DNS resolution)
    mapping(string => bytes32) public dnsToNode;

    /// Verification fee in wei (adjustable by owner / future DAO)
    uint256 public verificationFee = 1 ether;   // 1 MATIC on Polygon

    /// Minimum stake required to register
    uint256 public minStake = 0;

    address public owner;

    // ── Events ────────────────────────────────────────────────────────────────

    event NodeRegistered(
        bytes32 indexed nodeHash,
        address indexed wallet,
        string  dnsName,
        uint256 timestamp
    );

    event NodeVerified(
        bytes32 indexed nodeHash,
        address indexed wallet,
        uint256 timestamp
    );

    event StakeAdded(
        bytes32 indexed nodeHash,
        address indexed wallet,
        uint256 amount,
        uint256 newTotal
    );

    event StakeWithdrawn(
        bytes32 indexed nodeHash,
        address indexed wallet,
        uint256 amount
    );

    event NodeDeregistered(bytes32 indexed nodeHash);

    event VerificationFeeUpdated(uint256 oldFee, uint256 newFee);

    event OwnershipTransferred(address indexed oldOwner, address indexed newOwner);

    // ── Modifiers ─────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "BizNodeRegistry: not authorized");
        _;
    }

    modifier nodeExists(bytes32 nodeHash) {
        require(nodes[nodeHash].wallet != address(0), "BizNodeRegistry: node not registered");
        _;
    }

    modifier onlyNodeOwner(bytes32 nodeHash) {
        require(nodes[nodeHash].wallet == msg.sender, "BizNodeRegistry: not node owner");
        _;
    }

    // ── Constructor ───────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ── Core functions ────────────────────────────────────────────────────────

    /**
     * @notice Register a new BizNode on-chain.
     * @param nodeHash  keccak256(node_id) — computed off-chain in identity/wallet.py
     * @param dnsName   Human-readable 1bz alias, e.g. "shashi.1bz"
     */
    function registerNode(bytes32 nodeHash, string calldata dnsName) external payable {
        require(nodes[nodeHash].wallet == address(0), "BizNodeRegistry: already registered");
        require(dnsToNode[dnsName] == bytes32(0),     "BizNodeRegistry: DNS name already taken");
        require(bytes(dnsName).length > 0,            "BizNodeRegistry: dnsName cannot be empty");
        require(msg.value >= minStake,                "BizNodeRegistry: insufficient stake");

        nodes[nodeHash] = Node({
            wallet:       msg.sender,
            dnsName:      dnsName,
            verified:     false,
            stakeAmount:  msg.value,
            registeredAt: block.timestamp,
            active:       true
        });

        dnsToNode[dnsName] = nodeHash;

        emit NodeRegistered(nodeHash, msg.sender, dnsName, block.timestamp);

        if (msg.value > 0) {
            emit StakeAdded(nodeHash, msg.sender, msg.value, msg.value);
        }
    }

    /**
     * @notice Pay the verification fee to mark a node as verified.
     *         The fee is retained by the contract (withdrawable by owner / DAO).
     * @param nodeHash  The node to verify.
     */
    function verifyNode(bytes32 nodeHash)
        external
        payable
        nodeExists(nodeHash)
        onlyNodeOwner(nodeHash)
    {
        require(!nodes[nodeHash].verified, "BizNodeRegistry: already verified");
        require(msg.value >= verificationFee, "BizNodeRegistry: insufficient verification fee");

        nodes[nodeHash].verified = true;

        emit NodeVerified(nodeHash, msg.sender, block.timestamp);
    }

    /**
     * @notice Add stake to an existing node.
     * @param nodeHash  The node to stake on.
     */
    function addStake(bytes32 nodeHash)
        external
        payable
        nodeExists(nodeHash)
        onlyNodeOwner(nodeHash)
    {
        require(msg.value > 0, "BizNodeRegistry: stake must be > 0");

        nodes[nodeHash].stakeAmount += msg.value;

        emit StakeAdded(nodeHash, msg.sender, msg.value, nodes[nodeHash].stakeAmount);
    }

    /**
     * @notice Withdraw stake from a node (partial or full).
     * @param nodeHash  The node to withdraw from.
     * @param amount    Amount in wei to withdraw.
     */
    function withdrawStake(bytes32 nodeHash, uint256 amount)
        external
        nodeExists(nodeHash)
        onlyNodeOwner(nodeHash)
    {
        require(amount > 0, "BizNodeRegistry: amount must be > 0");
        require(nodes[nodeHash].stakeAmount >= amount, "BizNodeRegistry: insufficient stake");

        nodes[nodeHash].stakeAmount -= amount;

        (bool sent, ) = msg.sender.call{value: amount}("");
        require(sent, "BizNodeRegistry: transfer failed");

        emit StakeWithdrawn(nodeHash, msg.sender, amount);
    }

    /**
     * @notice Deregister a node (marks inactive, frees DNS name).
     * @param nodeHash  The node to deregister.
     */
    function deregisterNode(bytes32 nodeHash)
        external
        nodeExists(nodeHash)
        onlyNodeOwner(nodeHash)
    {
        string memory dns = nodes[nodeHash].dnsName;
        nodes[nodeHash].active = false;
        delete dnsToNode[dns];

        emit NodeDeregistered(nodeHash);
    }

    // ── DNS resolution ────────────────────────────────────────────────────────

    /**
     * @notice Resolve a 1bz DNS name to a nodeHash.
     * @param dnsName  e.g. "shashi.1bz"
     * @return nodeHash  The associated node hash, or bytes32(0) if not found.
     */
    function resolveDNS(string calldata dnsName) external view returns (bytes32) {
        return dnsToNode[dnsName];
    }

    /**
     * @notice Get full node metadata by nodeHash.
     */
    function getNode(bytes32 nodeHash)
        external
        view
        returns (
            address wallet,
            string memory dnsName,
            bool verified,
            uint256 stakeAmount,
            uint256 registeredAt,
            bool active
        )
    {
        Node storage n = nodes[nodeHash];
        return (n.wallet, n.dnsName, n.verified, n.stakeAmount, n.registeredAt, n.active);
    }

    // ── Admin functions ───────────────────────────────────────────────────────

    /**
     * @notice Update the verification fee. Callable by owner / future DAO.
     */
    function updateVerificationFee(uint256 newFee) external onlyOwner {
        emit VerificationFeeUpdated(verificationFee, newFee);
        verificationFee = newFee;
    }

    /**
     * @notice Update the minimum stake required to register.
     */
    function updateMinStake(uint256 newMinStake) external onlyOwner {
        minStake = newMinStake;
    }

    /**
     * @notice Withdraw accumulated verification fees to owner / DAO treasury.
     */
    function withdrawFees(address payable recipient, uint256 amount) external onlyOwner {
        require(amount <= address(this).balance, "BizNodeRegistry: insufficient balance");
        (bool sent, ) = recipient.call{value: amount}("");
        require(sent, "BizNodeRegistry: transfer failed");
    }

    /**
     * @notice Transfer contract ownership to a new address (e.g. DAO contract).
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "BizNodeRegistry: zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    // ── Fallback ──────────────────────────────────────────────────────────────

    receive() external payable {}
}
