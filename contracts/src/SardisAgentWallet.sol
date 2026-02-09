// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

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

    /// @notice Mapping of used signatures to prevent replay attacks
    mapping(bytes32 => bool) public usedSignatures;

    /// @notice Total amount held per token (to prevent over-commitment)
    mapping(address => uint256) public totalHeldAmount;

    /// @notice Allowed tokens (stablecoin allowlist - only these tokens can be transferred out)
    mapping(address => bool) public allowedTokens;

    /// @notice Whether token allowlist is enforced (default: true)
    bool public enforceTokenAllowlist = true;

    // ============ Sardis Transfer Timelock ============

    /// @notice Pending new Sardis address (two-step transfer)
    address public pendingSardis;

    /// @notice Timestamp when the Sardis transfer was proposed
    uint256 public sardisTransferTimestamp;

    /// @notice Timelock delay for Sardis role transfer (2 days)
    uint256 public constant SARDIS_TRANSFER_DELAY = 2 days;
    
    // ============ Structs ============
    
    struct Hold {
        address merchant;
        address token;
        uint256 amount;
        uint256 capturedAmount;
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
        address indexed token,
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

    event SignatureUsed(bytes32 indexed signatureHash, address indexed signer);

    event SardisTransferred(address indexed oldSardis, address indexed newSardis);

    event SardisTransferProposed(address indexed newSardis, uint256 executeAfter);

    event SardisTransferCancelled(address indexed cancelledSardis);

    event TokenAllowed(address indexed token);

    event TokenRemoved(address indexed token);

    event TokenAllowlistToggled(bool enforced);
    
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
        require(amount > 0, "Amount must be greater than zero");

        // Check token allowlist (stablecoin-only enforcement)
        _checkToken(token);

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
     * @param deadline Timestamp after which the signature expires
     * @param agentSignature Agent's signature approving this payment
     */
    function payWithCoSign(
        address token,
        address to,
        uint256 amount,
        string calldata purpose,
        uint256 deadline,
        bytes calldata agentSignature
    ) external onlySardis nonReentrant whenNotPaused returns (bytes32) {
        // Check signature deadline
        require(block.timestamp <= deadline, "Signature expired");

        // Create unique signature hash for replay protection
        bytes32 messageHash = keccak256(abi.encodePacked(
            address(this),
            token,
            to,
            amount,
            nonce,
            deadline,
            block.chainid
        ));

        // Check if signature has been used
        require(!usedSignatures[messageHash], "Signature already used");

        // Verify agent signature
        require(
            _verifySignature(messageHash, agentSignature, agent),
            "Invalid agent signature"
        );

        // Mark signature as used to prevent replay
        usedSignatures[messageHash] = true;
        emit SignatureUsed(messageHash, agent);

        // Check token allowlist (stablecoin-only enforcement)
        _checkToken(token);

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
        require(amount > 0, "Amount must be greater than zero");
        require(duration > 0 && duration <= 7 days, "Invalid duration");

        // Check token allowlist (stablecoin-only enforcement)
        _checkToken(token);

        // Check available balance (total balance minus already held amounts)
        uint256 balance = IERC20(token).balanceOf(address(this));
        uint256 available = balance > totalHeldAmount[token] ? balance - totalHeldAmount[token] : 0;
        require(available >= amount, "Insufficient available balance");

        _checkMerchant(merchant);
        _checkLimits(amount);

        // SECURITY: Holds MUST count toward daily limits. Without this, an agent
        // could create unlimited holds to bypass spending limits, then capture them.
        _updateSpentAmount(amount);

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
            capturedAmount: 0,
            createdAt: block.timestamp,
            expiresAt: block.timestamp + duration,
            captured: false,
            voided: false
        });

        // Track held amount
        totalHeldAmount[token] += amount;

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
        require(captureAmount > 0, "Capture amount must be greater than zero");
        require(!hold.captured, "Already captured");
        require(!hold.voided, "Hold voided");
        require(block.timestamp <= hold.expiresAt, "Hold expired");
        require(captureAmount <= hold.amount, "Amount exceeds hold");

        hold.captured = true;
        hold.capturedAmount = captureAmount;

        // Release full held amount: captured portion is transferred,
        // uncaptured remainder becomes available balance again
        totalHeldAmount[hold.token] -= hold.amount;

        // SECURITY: Do NOT call _updateSpentAmount here — the hold amount was
        // already counted toward the daily limit when the hold was created.
        // If capture < hold, the difference is "refunded" to the daily limit.
        if (captureAmount < hold.amount) {
            uint256 refundedAmount = hold.amount - captureAmount;
            // Give back the unused portion to the daily limit
            if (spentToday >= refundedAmount) {
                spentToday -= refundedAmount;
            } else {
                spentToday = 0;
            }
        }

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

        // Release held amount
        totalHeldAmount[hold.token] -= hold.amount;

        // SECURITY: Refund the daily limit since the hold was counted at creation
        if (spentToday >= hold.amount) {
            spentToday -= hold.amount;
        } else {
            spentToday = 0;
        }

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
    
    // ============ Token Allowlist (Stablecoin-Only) ============

    /**
     * @notice Add a token to the allowlist (e.g., USDC, USDT, EURC)
     * @dev Only Sardis can manage the token allowlist. Agents cannot whitelist
     *      arbitrary tokens — this prevents NFT/meme coin transfers.
     */
    function allowToken(address token) external onlySardis {
        require(token != address(0), "Invalid token");
        allowedTokens[token] = true;
        emit TokenAllowed(token);
    }

    /**
     * @notice Remove a token from the allowlist
     */
    function removeToken(address token) external onlySardis {
        allowedTokens[token] = false;
        emit TokenRemoved(token);
    }

    /**
     * @notice Toggle token allowlist enforcement
     * @dev When enabled, only whitelisted tokens (stablecoins) can be transferred.
     *      When disabled, any ERC20 can be transferred (useful for recovery).
     */
    function setTokenAllowlistEnforced(bool _enforced) external onlySardis {
        enforceTokenAllowlist = _enforced;
        emit TokenAllowlistToggled(_enforced);
    }

    /**
     * @notice Check if a token is allowed for transfers
     */
    function isTokenAllowed(address token) external view returns (bool) {
        if (!enforceTokenAllowlist) return true;
        return allowedTokens[token];
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
     * @dev SECURITY: Only withdraws available balance (total minus held amounts).
     *      Held funds belong to merchants with active pre-authorizations.
     *      Withdrawing held funds would break escrow guarantees.
     * @param token Token to withdraw
     */
    function emergencyWithdraw(address token) external onlyRecovery nonReentrant {
        uint256 balance = IERC20(token).balanceOf(address(this));
        uint256 held = totalHeldAmount[token];
        uint256 available = balance > held ? balance - held : 0;
        if (available > 0) {
            IERC20(token).safeTransfer(recoveryAddress, available);
        }
    }

    /**
     * @notice Emergency withdrawal of native ETH to recovery address
     * @dev SECURITY: Without this function, ETH sent to the wallet via receive()
     *      would be permanently locked with no way to retrieve it.
     */
    function emergencyWithdrawETH() external onlyRecovery nonReentrant {
        uint256 balance = address(this).balance;
        if (balance > 0) {
            (bool success, ) = recoveryAddress.call{value: balance}("");
            require(success, "ETH transfer failed");
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

    /**
     * @notice Propose transfer of Sardis role to a new address (step 1 of 2)
     * @dev SECURITY: Two-step timelock prevents instant takeover if Sardis key is
     *      compromised. The agent/recovery has SARDIS_TRANSFER_DELAY to detect and
     *      pause the wallet before the transfer completes.
     * @param _newSardis The proposed new Sardis platform address
     */
    function proposeSardisTransfer(address _newSardis) external onlySardis {
        require(_newSardis != address(0), "Invalid address");
        require(_newSardis != sardis, "Same address");

        pendingSardis = _newSardis;
        sardisTransferTimestamp = block.timestamp;

        emit SardisTransferProposed(_newSardis, block.timestamp + SARDIS_TRANSFER_DELAY);
    }

    /**
     * @notice Execute a proposed Sardis role transfer (step 2 of 2)
     * @dev Can only be called after the timelock delay has passed.
     */
    function executeSardisTransfer() external onlySardis {
        require(pendingSardis != address(0), "No pending transfer");
        require(
            block.timestamp >= sardisTransferTimestamp + SARDIS_TRANSFER_DELAY,
            "Timelock not expired"
        );

        address oldSardis = sardis;
        sardis = pendingSardis;
        pendingSardis = address(0);
        sardisTransferTimestamp = 0;

        emit SardisTransferred(oldSardis, sardis);
    }

    /**
     * @notice Cancel a pending Sardis role transfer
     * @dev Can be called by current Sardis or recovery address to abort a compromised transfer.
     */
    function cancelSardisTransfer() external {
        require(
            msg.sender == sardis || msg.sender == recoveryAddress,
            "Only Sardis or recovery"
        );
        require(pendingSardis != address(0), "No pending transfer");

        address cancelled = pendingSardis;
        pendingSardis = address(0);
        sardisTransferTimestamp = 0;

        emit SardisTransferCancelled(cancelled);
    }
    
    // ============ View Functions ============
    
    /**
     * @notice Get wallet balance for a token
     */
    function getBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }

    /**
     * @notice Get available balance (total balance minus held amounts)
     */
    function getAvailableBalance(address token) external view returns (uint256) {
        uint256 balance = IERC20(token).balanceOf(address(this));
        uint256 held = totalHeldAmount[token];
        return balance > held ? balance - held : 0;
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
    
    function _checkToken(address token) internal view {
        if (enforceTokenAllowlist) {
            require(allowedTokens[token], "Token not allowed (stablecoins only)");
        }
    }

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

        // Validate v value (must be 27 or 28)
        require(v == 27 || v == 28, "Invalid signature v value");

        // EIP-2: Enforce low-s to prevent signature malleability
        // secp256k1n / 2 = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0
        require(
            uint256(s) <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0,
            "Invalid signature s value"
        );
    }
    
    // ============ Receive ============
    
    receive() external payable {}
}

