// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title SimpleVault
 * @notice Single-owner escrow vault for PayDrive AI settlements.
 *         Owner deposits ETH, agent triggers release to vendor addresses.
 */
contract SimpleVault {
    address public owner;

    event Deposited(address indexed from, uint256 amount);
    event Released(bytes32 indexed invoiceId, address indexed recipient, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "SimpleVault: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Deposit ETH into the vault
    receive() external payable {
        emit Deposited(msg.sender, msg.value);
    }

    /// @notice Release funds to a recipient for a given invoice
    /// @param recipient The vendor's wallet address
    /// @param amount Amount in wei to release
    /// @param invoiceId Keccak256 hash of the invoice ID string
    function release(
        address payable recipient,
        uint256 amount,
        bytes32 invoiceId
    ) external onlyOwner {
        require(address(this).balance >= amount, "SimpleVault: insufficient balance");
        require(recipient != address(0), "SimpleVault: zero address");

        recipient.transfer(amount);
        emit Released(invoiceId, recipient, amount);
    }

    /// @notice Check vault balance
    function balance() external view returns (uint256) {
        return address(this).balance;
    }

    /// @notice Transfer ownership
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "SimpleVault: zero address");
        owner = newOwner;
    }
}
