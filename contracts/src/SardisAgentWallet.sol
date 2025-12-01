// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title SardisAgentWallet
 * @notice Programmable wallet for AI agents with on-chain spending controls
 * @dev Multi-sig wallet with Sardis as co-signer, enforcing spending limits on-chain
 * 
 * Features:
 * - Per-transaction spending limits
 * - Daily spending limits with automatic reset
 * - Merchant allowlist/denylist
 * - Emergency recovery mechanism
 * - Pre-authorization holds
 * - Gas abstraction (Sardis pays gas)
 */
contract SardisAgentWallet is ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ============ State Variables ============
    
    /// @notice The agent that owns this wallet
    address public agent;
    
    /// @notice Sardis platform address (co-signer)
    address public sardis;
    
    /// @notice Recovery address for emergencies
    address public recoveryAddress;
    
    /// @notice Maximum amount per transaction (in base units)
    uint256 public limitPerTx;
    
    /// @notice Maximum amount per day (in base units)
    uint256 public dailyLimit;
    
    /// @notice Amount spent today
    uint256 public spentToday;
    
    /// @notice Timestamp of last daily reset
    uint256 public lastResetDay;
    
    /// @notice Whether to use allowlist mode (true) or denylist mode (false)
    bool public useAllowlist;
    
    /// @notice Merchant allowlist (only pay these addresses)
    mapping(address => bool) public allowedMerchants;
    
    /// @notice Merchant denylist (never pay these addresses)
    mapping(address => bool) public deniedMerchants;
    
    /// @notice Active holds (pre-authorizations)
    mapping(bytes32 => Hold) public holds;
    
    /// @notice Nonce for transaction ordering
    uint256 public nonce;
    
    // ============ Structs ============
    
    struct Hold {
        address merchant;
        address token;
        uint256 amount;
        uint256 createdAt;
        uint256 expiresAt;
        bool captured;
        bool voided;
    }
    
    // ============ Events ============
    
    event Payment(
        address indexed token,
        address indexed to,
        uint256 amount,
        bytes32 indexed txHash,
        string purpose
    );
    
    event HoldCreated(
        bytes32 indexed holdId,
        address indexed merchant,
        address token,
        uint256 amount,
        uint256 expiresAt
    );
    
    event HoldCaptured(
        bytes32 indexed holdId,
        uint256 capturedAmount
    );
    
    event HoldVoided(bytes32 indexed holdId);
    
    event LimitsUpdated(uint256 limitPerTx, uint256 dailyLimit);
    
    event MerchantAllowed(address indexed merchant);
    
    event MerchantDenied(address indexed merchant);
    
    event MerchantRemoved(address indexed merchant);
    
    event RecoveryInitiated(address indexed recoveryAddress);
    
    // ============ Modifiers ============
    
    modifier onlyAgent() {
        require(msg.sender == agent, "Only agent");
        _;
    }
    
    modifier onlySardis() {
        require(msg.sender == sardis, "Only Sardis");
        _;
    }
    
    modifier onlyAgentOrSardis() {
        require(msg.sender == agent || msg.sender == sardis, "Only agent or Sardis");
        _;
    }
    
    modifier onlyRecovery() {
        require(msg.sender == recoveryAddress, "Only recovery");
        _;
    }
    
    // ============ Constructor ============
    
    constructor(
        address _agent,
        address _sardis,
        address _recoveryAddress,
        uint256 _limitPerTx,
        uint256 _dailyLimit
    ) {
        require(_agent != address(0), "Invalid agent");
        require(_sardis != address(0), "Invalid sardis");
        
        agent = _agent;
        sardis = _sardis;
        recoveryAddress = _recoveryAddress;
        limitPerTx = _limitPerTx;
        dailyLimit = _dailyLimit;
        lastResetDay = block.timestamp / 1 days;
    }
    
    // ============ Payment Functions ============
    
    /**
     * @notice Execute a payment to a merchant
     * @param token ERC20 token to pay with
     * @param to Recipient address
     * @param amount Amount to pay (in token's base units)
     * @param purpose Human-readable purpose for the payment
     */
    function pay(
        address token,
        address to,
        uint256 amount,
        string calldata purpose
    ) external onlyAgentOrSardis nonReentrant whenNotPaused returns (bytes32) {
        // Check merchant restrictions
        _checkMerchant(to);
        
        // Check spending limits
        _checkLimits(amount);
        
        // Update spent amount
        _updateSpentAmount(amount);
        
        // Execute transfer
        IERC20(token).safeTransfer(to, amount);
        
        // Generate transaction hash
        bytes32 txHash = keccak256(abi.encodePacked(
            address(this),
            token,
            to,
            amount,
            nonce++,
            block.timestamp
        ));
        
        emit Payment(token, to, amount, txHash, purpose);
        
        return txHash;
    }
    
    /**
     * @notice Execute a payment with Sardis co-signature (for higher limits)
     * @param token ERC20 token to pay with
     * @param to Recipient address
     * @param amount Amount to pay
     * @param purpose Human-readable purpose
     * @param agentSignature Agent's signature approving this payment
     */
    function payWithCoSign(
        address token,
        address to,
        uint256 amount,
        string calldata purpose,
        bytes calldata agentSignature
    ) external onlySardis nonReentrant whenNotPaused returns (bytes32) {
        // Verify agent signature
        bytes32 messageHash = keccak256(abi.encodePacked(
            address(this),
            token,
            to,
            amount,
            nonce,
            block.chainid
        ));
        
        require(
            _verifySignature(messageHash, agentSignature, agent),
            "Invalid agent signature"
        );
        
        // Check merchant restrictions (limits bypassed for co-signed tx)
        _checkMerchant(to);
        
        // Execute transfer
        IERC20(token).safeTransfer(to, amount);
        
        // Generate transaction hash
        bytes32 txHash = keccak256(abi.encodePacked(
            address(this),
            token,
            to,
            amount,
            nonce++,
            block.timestamp
        ));
        
        emit Payment(token, to, amount, txHash, purpose);
        
        return txHash;
    }
    
    // ============ Hold Functions (Pre-Authorization) ============
    
    /**
     * @notice Create a hold (pre-authorization) on funds
     * @param merchant Merchant this hold is for
     * @param token Token to hold
     * @param amount Amount to hold
     * @param duration How long until the hold expires (seconds)
     */
    function createHold(
        address merchant,
        address token,
        uint256 amount,
        uint256 duration
    ) external onlyAgentOrSardis returns (bytes32) {
        require(duration > 0 && duration <= 7 days, "Invalid duration");
        require(IERC20(token).balanceOf(address(this)) >= amount, "Insufficient balance");
        
        _checkMerchant(merchant);
        _checkLimits(amount);
        
        bytes32 holdId = keccak256(abi.encodePacked(
            address(this),
            merchant,
            token,
            amount,
            block.timestamp,
            nonce++
        ));
        
        holds[holdId] = Hold({
            merchant: merchant,
            token: token,
            amount: amount,
            createdAt: block.timestamp,
            expiresAt: block.timestamp + duration,
            captured: false,
            voided: false
        });
        
        emit HoldCreated(holdId, merchant, token, amount, block.timestamp + duration);
        
        return holdId;
    }
    
    /**
     * @notice Capture a hold (complete the payment)
     * @param holdId The hold to capture
     * @param captureAmount Amount to capture (can be less than hold amount)
     */
    function captureHold(
        bytes32 holdId,
        uint256 captureAmount
    ) external onlyAgentOrSardis nonReentrant {
        Hold storage hold = holds[holdId];
        
        require(hold.amount > 0, "Hold not found");
        require(!hold.captured, "Already captured");
        require(!hold.voided, "Hold voided");
        require(block.timestamp <= hold.expiresAt, "Hold expired");
        require(captureAmount <= hold.amount, "Amount exceeds hold");
        
        hold.captured = true;
        
        // Update spent amount
        _updateSpentAmount(captureAmount);
        
        // Execute transfer
        IERC20(hold.token).safeTransfer(hold.merchant, captureAmount);
        
        emit HoldCaptured(holdId, captureAmount);
    }
    
    /**
     * @notice Void a hold (cancel without payment)
     * @param holdId The hold to void
     */
    function voidHold(bytes32 holdId) external onlyAgentOrSardis {
        Hold storage hold = holds[holdId];
        
        require(hold.amount > 0, "Hold not found");
        require(!hold.captured, "Already captured");
        require(!hold.voided, "Already voided");
        
        hold.voided = true;
        
        emit HoldVoided(holdId);
    }
    
    // ============ Limit Management ============
    
    /**
     * @notice Update spending limits (requires Sardis approval)
     * @param _limitPerTx New per-transaction limit
     * @param _dailyLimit New daily limit
     */
    function setLimits(
        uint256 _limitPerTx,
        uint256 _dailyLimit
    ) external onlySardis {
        limitPerTx = _limitPerTx;
        dailyLimit = _dailyLimit;
        
        emit LimitsUpdated(_limitPerTx, _dailyLimit);
    }
    
    /**
     * @notice Add a merchant to the allowlist
     */
    function allowMerchant(address merchant) external onlyAgentOrSardis {
        allowedMerchants[merchant] = true;
        deniedMerchants[merchant] = false;
        
        emit MerchantAllowed(merchant);
    }
    
    /**
     * @notice Add a merchant to the denylist
     */
    function denyMerchant(address merchant) external onlyAgentOrSardis {
        deniedMerchants[merchant] = true;
        allowedMerchants[merchant] = false;
        
        emit MerchantDenied(merchant);
    }
    
    /**
     * @notice Remove a merchant from both lists
     */
    function removeMerchant(address merchant) external onlyAgentOrSardis {
        allowedMerchants[merchant] = false;
        deniedMerchants[merchant] = false;
        
        emit MerchantRemoved(merchant);
    }
    
    /**
     * @notice Toggle between allowlist and denylist mode
     */
    function setAllowlistMode(bool _useAllowlist) external onlySardis {
        useAllowlist = _useAllowlist;
    }
    
    // ============ Emergency Functions ============
    
    /**
     * @notice Pause the wallet (emergency stop)
     */
    function pause() external onlyAgentOrSardis {
        _pause();
    }
    
    /**
     * @notice Unpause the wallet
     */
    function unpause() external onlySardis {
        _unpause();
    }
    
    /**
     * @notice Emergency withdrawal to recovery address
     * @param token Token to withdraw
     */
    function emergencyWithdraw(address token) external onlyRecovery {
        uint256 balance = IERC20(token).balanceOf(address(this));
        if (balance > 0) {
            IERC20(token).safeTransfer(recoveryAddress, balance);
        }
    }
    
    /**
     * @notice Update recovery address
     */
    function setRecoveryAddress(address _recoveryAddress) external onlySardis {
        require(_recoveryAddress != address(0), "Invalid address");
        recoveryAddress = _recoveryAddress;
        
        emit RecoveryInitiated(_recoveryAddress);
    }
    
    // ============ View Functions ============
    
    /**
     * @notice Get wallet balance for a token
     */
    function getBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }
    
    /**
     * @notice Get remaining daily limit
     */
    function getRemainingDailyLimit() external view returns (uint256) {
        uint256 today = block.timestamp / 1 days;
        if (today > lastResetDay) {
            return dailyLimit;
        }
        return dailyLimit > spentToday ? dailyLimit - spentToday : 0;
    }
    
    /**
     * @notice Check if a payment would be allowed
     */
    function canPay(
        address to,
        uint256 amount
    ) external view returns (bool allowed, string memory reason) {
        // Check merchant
        if (useAllowlist && !allowedMerchants[to]) {
            return (false, "Merchant not in allowlist");
        }
        if (deniedMerchants[to]) {
            return (false, "Merchant denied");
        }
        
        // Check per-tx limit
        if (amount > limitPerTx) {
            return (false, "Exceeds per-transaction limit");
        }
        
        // Check daily limit
        uint256 today = block.timestamp / 1 days;
        uint256 todaySpent = today > lastResetDay ? 0 : spentToday;
        if (todaySpent + amount > dailyLimit) {
            return (false, "Exceeds daily limit");
        }
        
        return (true, "");
    }
    
    // ============ Internal Functions ============
    
    function _checkMerchant(address merchant) internal view {
        if (useAllowlist) {
            require(allowedMerchants[merchant], "Merchant not allowed");
        }
        require(!deniedMerchants[merchant], "Merchant denied");
    }
    
    function _checkLimits(uint256 amount) internal view {
        require(amount <= limitPerTx, "Exceeds per-tx limit");
        
        uint256 today = block.timestamp / 1 days;
        uint256 todaySpent = today > lastResetDay ? 0 : spentToday;
        require(todaySpent + amount <= dailyLimit, "Exceeds daily limit");
    }
    
    function _updateSpentAmount(uint256 amount) internal {
        uint256 today = block.timestamp / 1 days;
        
        if (today > lastResetDay) {
            spentToday = amount;
            lastResetDay = today;
        } else {
            spentToday += amount;
        }
    }
    
    function _verifySignature(
        bytes32 messageHash,
        bytes calldata signature,
        address signer
    ) internal pure returns (bool) {
        bytes32 ethSignedHash = keccak256(abi.encodePacked(
            "\x19Ethereum Signed Message:\n32",
            messageHash
        ));
        
        (bytes32 r, bytes32 s, uint8 v) = _splitSignature(signature);
        address recovered = ecrecover(ethSignedHash, v, r, s);
        
        return recovered == signer;
    }
    
    function _splitSignature(bytes calldata sig) internal pure returns (bytes32 r, bytes32 s, uint8 v) {
        require(sig.length == 65, "Invalid signature length");
        
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
    }
    
    // ============ Receive ============
    
    receive() external payable {}
}

