// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title SignalAttestor
/// @notice Minimal commit-reveal notary for trading signals. The owner commits a
///         hash of a signal each hour BEFORE the market outcome is known, then later
///         reveals the underlying payload. Anyone can recompute the hash from the
///         revealed payload + salt and check it against the on-chain commit and its
///         block timestamp — proving the signal predated the outcome and was not
///         altered. Holds no funds, makes no external calls, is not upgradeable.
///
///         Hash recipe (see README): hash = keccak256(canonical_json_bytes || salt)
///         where canonical JSON has sorted keys, no whitespace, UTF-8; salt is 32
///         random bytes stored locally per commit.
contract SignalAttestor {
    address public immutable owner;
    uint256 public commitCount;

    struct Commit {
        bytes32 hash;
        uint64 timestamp;   // block.timestamp at commit (seconds, UTC)
        bool revealed;
    }

    mapping(uint256 => Commit) public commits;

    event Committed(uint256 indexed id, bytes32 hash, uint256 timestamp);
    event Revealed(uint256 indexed id, string payloadURI, bytes32 salt);

    error NotOwner();
    error BadId();
    error AlreadyRevealed();

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    /// @notice Notarize a signal hash. Returns the assigned commit id.
    function commit(bytes32 hash) external onlyOwner returns (uint256 id) {
        id = commitCount++;
        commits[id] = Commit({hash: hash, timestamp: uint64(block.timestamp), revealed: false});
        emit Committed(id, hash, block.timestamp);
    }

    /// @notice Reveal the payload behind a prior commit. Does not re-store the payload
    ///         on-chain (kept cheap); the event carries the URI + salt for verifiers.
    function reveal(uint256 id, string calldata payloadURI, bytes32 salt) external onlyOwner {
        if (id >= commitCount) revert BadId();
        Commit storage c = commits[id];
        if (c.revealed) revert AlreadyRevealed();
        c.revealed = true;
        emit Revealed(id, payloadURI, salt);
    }

    /// @notice Read a commit's stored fields.
    function getCommit(uint256 id) external view returns (bytes32 hash, uint64 timestamp, bool revealed) {
        Commit storage c = commits[id];
        return (c.hash, c.timestamp, c.revealed);
    }
}
