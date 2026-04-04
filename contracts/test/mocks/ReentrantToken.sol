// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ReentrantToken
/// @notice Mock ERC20 that calls back into the caller during transfer/transferFrom.
/// @dev Used to test reentrancy resistance in RefundProtocol and SardisVerifyingPaymaster.
///      The callback target and calldata are configurable so the same mock can attack
///      any external function.
contract ReentrantToken {
    string public name = "ReentrantToken";
    string public symbol = "REENT";
    uint8 public decimals = 6;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    /// @notice When set, transfer() will call this target with the given data before completing.
    address public callbackTarget;
    bytes public callbackData;
    bool public reentrancyEnabled;

    /// @notice Track how many times the callback was triggered
    uint256 public callbackCount;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
    }

    function setReentrancyCallback(address target, bytes calldata data) external {
        callbackTarget = target;
        callbackData = data;
        reentrancyEnabled = true;
    }

    function disableReentrancy() external {
        reentrancyEnabled = false;
    }

    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;

        if (reentrancyEnabled && callbackTarget != address(0)) {
            callbackCount++;
            // Attempt reentrancy: call back into the target contract
            (bool success,) = callbackTarget.call(callbackData);
            // We don't revert on failure - this lets the test check whether
            // the target contract properly rejected the reentrant call
            success; // silence warning
        }

        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(balanceOf[from] >= amount, "insufficient balance");
        require(allowance[from][msg.sender] >= amount, "insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;

        if (reentrancyEnabled && callbackTarget != address(0)) {
            callbackCount++;
            (bool success,) = callbackTarget.call(callbackData);
            success; // silence warning
        }

        return true;
    }
}
