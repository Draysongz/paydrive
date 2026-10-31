// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title MultiSigVault
 * @notice N-of-M multi-signature escrow vault for PayDrive AI settlements.
 *         Requires threshold confirmations before releasing funds.
 */
contract MultiSigVault {
    // --- State ---
    address[] public signers;
    mapping(address => bool) public isSigner;
    uint256 public threshold;
    uint256 public txCount;

    struct ReleaseTx {
        address payable recipient;
        uint256 amount;
        bytes32 invoiceId;
        uint256 confirmations;
        bool executed;
        uint256 createdAt;
    }

    mapping(uint256 => ReleaseTx) public transactions;
    mapping(uint256 => mapping(address => bool)) public confirmations;

    // --- Events ---
    event Deposited(address indexed from, uint256 amount);
    event Submitted(uint256 indexed txId, address indexed recipient, uint256 amount, bytes32 invoiceId);
    event Confirmed(uint256 indexed txId, address indexed signer);
    event Executed(uint256 indexed txId, address indexed recipient, uint256 amount, bytes32 invoiceId);
    event Revoked(uint256 indexed txId, address indexed signer);

    // --- Modifiers ---
    modifier onlySigner() {
        require(isSigner[msg.sender], "MultiSigVault: not signer");
        _;
    }

    modifier txExists(uint256 txId) {
        require(txId < txCount, "MultiSigVault: tx does not exist");
        _;
    }

    modifier notExecuted(uint256 txId) {
        require(!transactions[txId].executed, "MultiSigVault: already executed");
        _;
    }

    // --- Constructor ---
    constructor(address[] memory _signers, uint256 _threshold) {
        require(_signers.length >= _threshold, "MultiSigVault: invalid threshold");
        require(_threshold > 0, "MultiSigVault: threshold must be > 0");

        for (uint256 i = 0; i < _signers.length; i++) {
            address signer = _signers[i];
            require(signer != address(0), "MultiSigVault: zero address");
            require(!isSigner[signer], "MultiSigVault: duplicate signer");
            isSigner[signer] = true;
            signers.push(signer);
        }
        threshold = _threshold;
    }

    /// @notice Deposit ETH
    receive() external payable {
        emit Deposited(msg.sender, msg.value);
    }

    /// @notice Submit a new release transaction
    function submitRelease(
        address payable recipient,
        uint256 amount,
        bytes32 invoiceId
    ) external onlySigner returns (uint256) {
        require(recipient != address(0), "MultiSigVault: zero address");

        uint256 txId = txCount++;
        transactions[txId] = ReleaseTx({
            recipient: recipient,
            amount: amount,
            invoiceId: invoiceId,
            confirmations: 0,
            executed: false,
            createdAt: block.timestamp
        });

        emit Submitted(txId, recipient, amount, invoiceId);

        // Auto-confirm by submitter
        _confirm(txId);

        return txId;
    }

    /// @notice Confirm a pending transaction
    function confirmRelease(uint256 txId) external onlySigner txExists(txId) notExecuted(txId) {
        _confirm(txId);
    }

    /// @notice Revoke a confirmation
    function revokeConfirmation(uint256 txId) external onlySigner txExists(txId) notExecuted(txId) {
        require(confirmations[txId][msg.sender], "MultiSigVault: not confirmed");
        confirmations[txId][msg.sender] = false;
        transactions[txId].confirmations--;
        emit Revoked(txId, msg.sender);
    }

    /// @notice Get signer count
    function getSignerCount() external view returns (uint256) {
        return signers.length;
    }

    /// @notice Get transaction details
    function getTransaction(uint256 txId) external view returns (
        address recipient, uint256 amount, bytes32 invoiceId,
        uint256 confs, bool executed, uint256 createdAt
    ) {
        ReleaseTx storage t = transactions[txId];
        return (t.recipient, t.amount, t.invoiceId, t.confirmations, t.executed, t.createdAt);
    }

    /// @notice Check vault balance
    function balance() external view returns (uint256) {
        return address(this).balance;
    }

    // --- Internal ---
    function _confirm(uint256 txId) internal {
        require(!confirmations[txId][msg.sender], "MultiSigVault: already confirmed");
        confirmations[txId][msg.sender] = true;
        transactions[txId].confirmations++;
        emit Confirmed(txId, msg.sender);

        // Auto-execute if threshold met
        if (transactions[txId].confirmations >= threshold) {
            _execute(txId);
        }
    }

    function _execute(uint256 txId) internal {
        ReleaseTx storage t = transactions[txId];
        require(address(this).balance >= t.amount, "MultiSigVault: insufficient balance");

        t.executed = true;
        t.recipient.transfer(t.amount);

        emit Executed(txId, t.recipient, t.amount, t.invoiceId);
    }
}
