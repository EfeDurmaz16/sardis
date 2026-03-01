// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title SardisPolicyModule
 * @notice Safe module that enforces spending policies for AI agent wallets
 * @dev Attached to a Safe proxy — called via checkTransaction() before every tx.
 *
 * Replicates the policy logic from SardisAgentWallet but as a standalone module
 * that works with Safe Smart Accounts (audited, $100B+ TVL).
 *
 * Features:
 * - Per-transaction + daily spending limits (configurable by Sardis)
 * - Co-sign mode: agent + Sardis co-signer for elevated limits (10x default)
 * - Merchant allowlist/denylist per wallet
 * - Token allowlist enforcement (stablecoin-only by default)
 * - Pause/unpause per wallet
 */
contract SardisPolicyModule {
    // ============ State Variables ============

    /// @notice Sardis platform address (admin)
    address public sardis;

    /// @notice Per-wallet policy configuration
    mapping(address => WalletPolicy) public policies;

    /// @notice Per-wallet merchant allowlist
    mapping(address => mapping(address => bool)) public allowedMerchants;

    /// @notice Per-wallet merchant denylist
    mapping(address => mapping(address => bool)) public deniedMerchants;

    /// @notice Per-wallet token allowlist
    mapping(address => mapping(address => bool)) public allowedTokens;

    /// @notice Per-wallet daily spend tracking
    mapping(address => uint256) public spentToday;

    /// @notice Per-wallet last daily reset timestamp
    mapping(address => uint256) public lastResetDay;

    // ============ Structs ============

    struct WalletPolicy {
        uint256 limitPerTx;
        uint256 dailyLimit;
        uint256 coSignLimitPerTx;
        uint256 coSignDailyLimit;
        bool useAllowlist;
        bool enforceTokenAllowlist;
        bool paused;
        bool initialized;
    }

    // ============ Events ============

    event WalletInitialized(address indexed safe, uint256 limitPerTx, uint256 dailyLimit);
    event LimitsUpdated(
        address indexed safe, uint256 limitPerTx, uint256 dailyLimit, uint256 coSignLimitPerTx, uint256 coSignDailyLimit
    );
    event WalletPaused(address indexed safe);
    event WalletUnpaused(address indexed safe);
    event MerchantAllowed(address indexed safe, address indexed merchant);
    event MerchantDenied(address indexed safe, address indexed merchant);
    event MerchantRemoved(address indexed safe, address indexed merchant);
    event TokenAllowed(address indexed safe, address indexed token);
    event TokenRemoved(address indexed safe, address indexed token);
    event TokenAllowlistToggled(address indexed safe, bool enforced);
    event AllowlistModeSet(address indexed safe, bool useAllowlist);
    event TransactionChecked(address indexed safe, address indexed to, uint256 value);
    event SardisTransferred(address indexed oldSardis, address indexed newSardis);

    // ============ Modifiers ============

    modifier onlySardis() {
        require(msg.sender == sardis, "Only Sardis");
        _;
    }

    modifier walletInitialized(address safe) {
        require(policies[safe].initialized, "Wallet not initialized");
        _;
    }

    // ============ Constructor ============

    constructor(address _sardis) {
        require(_sardis != address(0), "Invalid sardis");
        sardis = _sardis;
    }

    // ============ Wallet Initialization ============

    /**
     * @notice Initialize policy for a new Safe wallet
     * @param safe The Safe proxy address
     * @param _limitPerTx Per-transaction spending limit
     * @param _dailyLimit Daily spending limit
     */
    function initializeWallet(address safe, uint256 _limitPerTx, uint256 _dailyLimit) external onlySardis {
        require(!policies[safe].initialized, "Already initialized");
        require(safe != address(0), "Invalid safe");

        policies[safe] = WalletPolicy({
            limitPerTx: _limitPerTx,
            dailyLimit: _dailyLimit,
            coSignLimitPerTx: _limitPerTx * 10,
            coSignDailyLimit: _dailyLimit * 10,
            useAllowlist: false,
            enforceTokenAllowlist: true,
            paused: false,
            initialized: true
        });

        lastResetDay[safe] = block.timestamp / 1 days;

        emit WalletInitialized(safe, _limitPerTx, _dailyLimit);
    }

    // ============ Transaction Guard (Safe calls this) ============

    /**
     * @notice Check if a transaction should be allowed
     * @dev Called by the Safe before executing any transaction.
     *      Reverts if the transaction violates policy.
     * @param safe The Safe wallet address
     * @param to Destination address
     * @param value ETH value being sent
     * @param data Transaction calldata
     */
    function checkTransaction(address safe, address to, uint256 value, bytes calldata data)
        external
        walletInitialized(safe)
    {
        WalletPolicy storage policy = policies[safe];
        require(!policy.paused, "Wallet paused");

        // If sending ETH directly, check limits on value
        if (value > 0) {
            _checkMerchant(safe, to);
            _checkLimits(safe, value);
            _updateSpentAmount(safe, value);
            emit TransactionChecked(safe, to, value);
            return;
        }

        // Detect ERC-20 transfer(address,uint256) or approve(address,uint256)
        if (data.length >= 68) {
            bytes4 selector = bytes4(data[:4]);

            // transfer(address,uint256) = 0xa9059cbb
            // approve(address,uint256) = 0x095ea7b3
            if (selector == 0xa9059cbb || selector == 0x095ea7b3) {
                // Token address is `to` (the ERC-20 contract)
                if (policy.enforceTokenAllowlist) {
                    require(allowedTokens[safe][to], "Token not allowed");
                }

                // Decode recipient and amount
                (address recipient, uint256 amount) = abi.decode(data[4:68], (address, uint256));

                _checkMerchant(safe, recipient);
                _checkLimits(safe, amount);
                _updateSpentAmount(safe, amount);
                emit TransactionChecked(safe, recipient, amount);
                return;
            }
        }

        // For other calls (e.g., contract interactions), check merchant only
        _checkMerchant(safe, to);
        emit TransactionChecked(safe, to, value);
    }

    /**
     * @notice Check a co-signed transaction (elevated limits)
     * @dev Called when both agent + Sardis approve the transaction
     * @param safe The Safe wallet address
     * @param to Destination address
     * @param value ETH value being sent
     * @param data Transaction calldata
     */
    function checkCoSignedTransaction(address safe, address to, uint256 value, bytes calldata data)
        external
        onlySardis
        walletInitialized(safe)
    {
        WalletPolicy storage policy = policies[safe];
        require(!policy.paused, "Wallet paused");

        if (value > 0) {
            _checkMerchant(safe, to);
            _checkCoSignLimits(safe, value);
            _updateSpentAmount(safe, value);
            emit TransactionChecked(safe, to, value);
            return;
        }

        if (data.length >= 68) {
            bytes4 selector = bytes4(data[:4]);
            if (selector == 0xa9059cbb || selector == 0x095ea7b3) {
                if (policy.enforceTokenAllowlist) {
                    require(allowedTokens[safe][to], "Token not allowed");
                }
                (address recipient, uint256 amount) = abi.decode(data[4:68], (address, uint256));
                _checkMerchant(safe, recipient);
                _checkCoSignLimits(safe, amount);
                _updateSpentAmount(safe, amount);
                emit TransactionChecked(safe, recipient, amount);
                return;
            }
        }

        _checkMerchant(safe, to);
        emit TransactionChecked(safe, to, value);
    }

    // ============ Policy Management ============

    function setLimits(
        address safe,
        uint256 _limitPerTx,
        uint256 _dailyLimit,
        uint256 _coSignLimitPerTx,
        uint256 _coSignDailyLimit
    ) external onlySardis walletInitialized(safe) {
        require(_coSignLimitPerTx >= _limitPerTx, "Co-sign per-tx must be >= normal");
        require(_coSignDailyLimit >= _dailyLimit, "Co-sign daily must be >= normal");

        WalletPolicy storage policy = policies[safe];
        policy.limitPerTx = _limitPerTx;
        policy.dailyLimit = _dailyLimit;
        policy.coSignLimitPerTx = _coSignLimitPerTx;
        policy.coSignDailyLimit = _coSignDailyLimit;

        emit LimitsUpdated(safe, _limitPerTx, _dailyLimit, _coSignLimitPerTx, _coSignDailyLimit);
    }

    function pause(address safe) external onlySardis walletInitialized(safe) {
        policies[safe].paused = true;
        emit WalletPaused(safe);
    }

    function unpause(address safe) external onlySardis walletInitialized(safe) {
        policies[safe].paused = false;
        emit WalletUnpaused(safe);
    }

    function setAllowlistMode(address safe, bool _useAllowlist) external onlySardis walletInitialized(safe) {
        policies[safe].useAllowlist = _useAllowlist;
        emit AllowlistModeSet(safe, _useAllowlist);
    }

    // ============ Merchant Management ============

    function allowMerchant(address safe, address merchant) external onlySardis walletInitialized(safe) {
        allowedMerchants[safe][merchant] = true;
        deniedMerchants[safe][merchant] = false;
        emit MerchantAllowed(safe, merchant);
    }

    function denyMerchant(address safe, address merchant) external onlySardis walletInitialized(safe) {
        deniedMerchants[safe][merchant] = true;
        allowedMerchants[safe][merchant] = false;
        emit MerchantDenied(safe, merchant);
    }

    function removeMerchant(address safe, address merchant) external onlySardis walletInitialized(safe) {
        allowedMerchants[safe][merchant] = false;
        deniedMerchants[safe][merchant] = false;
        emit MerchantRemoved(safe, merchant);
    }

    // ============ Token Allowlist ============

    function allowToken(address safe, address token) external onlySardis walletInitialized(safe) {
        require(token != address(0), "Invalid token");
        allowedTokens[safe][token] = true;
        emit TokenAllowed(safe, token);
    }

    function removeToken(address safe, address token) external onlySardis walletInitialized(safe) {
        allowedTokens[safe][token] = false;
        emit TokenRemoved(safe, token);
    }

    function setTokenAllowlistEnforced(address safe, bool _enforced) external onlySardis walletInitialized(safe) {
        policies[safe].enforceTokenAllowlist = _enforced;
        emit TokenAllowlistToggled(safe, _enforced);
    }

    // ============ Admin ============

    function transferSardis(address _newSardis) external onlySardis {
        require(_newSardis != address(0), "Invalid address");
        address old = sardis;
        sardis = _newSardis;
        emit SardisTransferred(old, _newSardis);
    }

    // ============ View Functions ============

    function getPolicy(address safe) external view returns (WalletPolicy memory) {
        return policies[safe];
    }

    function getRemainingDailyLimit(address safe) external view returns (uint256) {
        WalletPolicy storage policy = policies[safe];
        uint256 today = block.timestamp / 1 days;
        if (today > lastResetDay[safe]) {
            return policy.dailyLimit;
        }
        return policy.dailyLimit > spentToday[safe] ? policy.dailyLimit - spentToday[safe] : 0;
    }

    function isTokenAllowed(address safe, address token) external view returns (bool) {
        if (!policies[safe].enforceTokenAllowlist) return true;
        return allowedTokens[safe][token];
    }

    // ============ Internal Functions ============

    function _checkMerchant(address safe, address merchant) internal view {
        WalletPolicy storage policy = policies[safe];
        if (policy.useAllowlist) {
            require(allowedMerchants[safe][merchant], "Merchant not allowed");
        }
        require(!deniedMerchants[safe][merchant], "Merchant denied");
    }

    function _checkLimits(address safe, uint256 amount) internal view {
        WalletPolicy storage policy = policies[safe];
        require(amount <= policy.limitPerTx, "Exceeds per-tx limit");

        uint256 today = block.timestamp / 1 days;
        uint256 todaySpent = today > lastResetDay[safe] ? 0 : spentToday[safe];
        require(todaySpent + amount <= policy.dailyLimit, "Exceeds daily limit");
    }

    function _checkCoSignLimits(address safe, uint256 amount) internal view {
        WalletPolicy storage policy = policies[safe];
        require(amount <= policy.coSignLimitPerTx, "Exceeds co-sign per-tx limit");

        uint256 today = block.timestamp / 1 days;
        uint256 todaySpent = today > lastResetDay[safe] ? 0 : spentToday[safe];
        require(todaySpent + amount <= policy.coSignDailyLimit, "Exceeds co-sign daily limit");
    }

    function _updateSpentAmount(address safe, uint256 amount) internal {
        uint256 today = block.timestamp / 1 days;
        if (today > lastResetDay[safe]) {
            spentToday[safe] = amount;
            lastResetDay[safe] = today;
        } else {
            spentToday[safe] += amount;
        }
    }
}
