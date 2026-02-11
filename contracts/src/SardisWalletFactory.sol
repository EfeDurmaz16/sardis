// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/Address.sol";
import "./SardisAgentWallet.sol";

/**
 * @title SardisWalletFactory
 * @notice Factory contract for deploying SardisAgentWallet contracts
 * @dev Deployed and managed by Sardis platform
 * 
 * Features:
 * - Deploy new agent wallets
 * - Track all deployed wallets
 * - Configure default limits
 * - Manage platform-wide settings
 */
contract SardisWalletFactory is Ownable, Pausable {
    using Address for address payable;

    // ============ State Variables ============
    
    /// @notice Default per-transaction limit for new wallets (in base units)
    uint256 public defaultLimitPerTx;
    
    /// @notice Default daily limit for new wallets (in base units)
    uint256 public defaultDailyLimit;
    
    /// @notice Default recovery address for new wallets
    address public defaultRecoveryAddress;
    
    /// @notice Mapping of agent address to their wallets
    mapping(address => address[]) public agentWallets;
    
    /// @notice Mapping of wallet address to agent address
    mapping(address => address) public walletToAgent;
    
    /// @notice List of all deployed wallets
    address[] public allWallets;
    
    /// @notice Wallet deployment fee (in ETH/native token)
    uint256 public deploymentFee;
    
    /// @notice Whether an address is a valid Sardis wallet
    mapping(address => bool) public isValidWallet;
    
    // ============ Events ============
    
    event WalletCreated(
        address indexed agent,
        address indexed wallet,
        uint256 limitPerTx,
        uint256 dailyLimit
    );
    
    event DefaultLimitsUpdated(
        uint256 limitPerTx,
        uint256 dailyLimit
    );
    
    event DeploymentFeeUpdated(uint256 newFee);
    
    event RecoveryAddressUpdated(address indexed newAddress);
    
    event FeesWithdrawn(address indexed to, uint256 amount);
    
    // ============ Constructor ============
    
    constructor(
        uint256 _defaultLimitPerTx,
        uint256 _defaultDailyLimit,
        address _defaultRecoveryAddress
    ) Ownable(msg.sender) {
        defaultLimitPerTx = _defaultLimitPerTx;
        defaultDailyLimit = _defaultDailyLimit;
        defaultRecoveryAddress = _defaultRecoveryAddress;
    }
    
    // ============ Wallet Creation ============
    
    /**
     * @notice Create a new agent wallet with default limits
     * @param agent The agent address that will own this wallet
     * @return wallet The address of the newly created wallet
     */
    function createWallet(address agent) external payable whenNotPaused returns (address wallet) {
        return createWalletWithLimits(agent, defaultLimitPerTx, defaultDailyLimit);
    }
    
    /**
     * @notice Create a new agent wallet with custom limits
     * @param agent The agent address that will own this wallet
     * @param limitPerTx Per-transaction limit
     * @param dailyLimit Daily spending limit
     * @return wallet The address of the newly created wallet
     */
    function createWalletWithLimits(
        address agent,
        uint256 limitPerTx,
        uint256 dailyLimit
    ) public payable whenNotPaused returns (address wallet) {
        require(agent != address(0), "Invalid agent address");
        require(msg.value >= deploymentFee, "Insufficient deployment fee");
        
        // Deploy new wallet
        SardisAgentWallet newWallet = new SardisAgentWallet(
            agent,
            address(this), // Factory is initial Sardis address (can be updated)
            defaultRecoveryAddress,
            limitPerTx,
            dailyLimit
        );
        
        wallet = address(newWallet);
        
        // Track the wallet
        agentWallets[agent].push(wallet);
        walletToAgent[wallet] = agent;
        allWallets.push(wallet);
        isValidWallet[wallet] = true;
        
        // Refund excess ETH using sendValue for safer transfer
        if (msg.value > deploymentFee && deploymentFee > 0) {
            payable(msg.sender).sendValue(msg.value - deploymentFee);
        }
        
        emit WalletCreated(agent, wallet, limitPerTx, dailyLimit);
    }
    
    /**
     * @notice Create wallet with CREATE2 for deterministic addresses
     * @param agent The agent address
     * @param salt Unique salt for CREATE2
     * @return wallet The deterministic wallet address
     */
    function createWalletDeterministic(
        address agent,
        bytes32 salt
    ) external payable whenNotPaused returns (address wallet) {
        require(agent != address(0), "Invalid agent address");
        require(msg.value >= deploymentFee, "Insufficient deployment fee");
        
        // Compute deterministic salt including agent
        bytes32 finalSalt = keccak256(abi.encodePacked(agent, salt));
        
        // Deploy with CREATE2
        bytes memory bytecode = abi.encodePacked(
            type(SardisAgentWallet).creationCode,
            abi.encode(
                agent,
                address(this),
                defaultRecoveryAddress,
                defaultLimitPerTx,
                defaultDailyLimit
            )
        );
        
        assembly {
            wallet := create2(0, add(bytecode, 32), mload(bytecode), finalSalt)
        }
        
        require(wallet != address(0), "Create2 failed");
        
        // Track the wallet
        agentWallets[agent].push(wallet);
        walletToAgent[wallet] = agent;
        allWallets.push(wallet);
        isValidWallet[wallet] = true;
        
        // Refund excess using sendValue for safer transfer
        if (msg.value > deploymentFee && deploymentFee > 0) {
            payable(msg.sender).sendValue(msg.value - deploymentFee);
        }
        
        emit WalletCreated(agent, wallet, defaultLimitPerTx, defaultDailyLimit);
    }
    
    /**
     * @notice Predict the address of a wallet before deployment
     * @param agent The agent address
     * @param salt Unique salt
     * @return predicted The predicted wallet address
     */
    function predictWalletAddress(
        address agent,
        bytes32 salt
    ) external view returns (address predicted) {
        bytes32 finalSalt = keccak256(abi.encodePacked(agent, salt));
        
        bytes memory bytecode = abi.encodePacked(
            type(SardisAgentWallet).creationCode,
            abi.encode(
                agent,
                address(this),
                defaultRecoveryAddress,
                defaultLimitPerTx,
                defaultDailyLimit
            )
        );
        
        bytes32 hash = keccak256(abi.encodePacked(
            bytes1(0xff),
            address(this),
            finalSalt,
            keccak256(bytecode)
        ));
        
        predicted = address(uint160(uint256(hash)));
    }
    
    // ============ Admin Functions ============
    
    /**
     * @notice Update default limits for new wallets
     */
    function setDefaultLimits(
        uint256 _limitPerTx,
        uint256 _dailyLimit
    ) external onlyOwner {
        defaultLimitPerTx = _limitPerTx;
        defaultDailyLimit = _dailyLimit;
        
        emit DefaultLimitsUpdated(_limitPerTx, _dailyLimit);
    }
    
    /**
     * @notice Update deployment fee
     */
    function setDeploymentFee(uint256 _fee) external onlyOwner {
        deploymentFee = _fee;
        
        emit DeploymentFeeUpdated(_fee);
    }
    
    /**
     * @notice Update default recovery address
     */
    function setDefaultRecoveryAddress(address _address) external onlyOwner {
        require(_address != address(0), "Invalid address");
        defaultRecoveryAddress = _address;
        
        emit RecoveryAddressUpdated(_address);
    }
    
    /**
     * @notice Withdraw collected fees
     */
    function withdrawFees(address to) external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No fees to withdraw");

        // Use sendValue for safer ETH transfer (avoids transfer gas limit issues)
        payable(to).sendValue(balance);

        emit FeesWithdrawn(to, balance);
    }
    
    /**
     * @notice Pause factory (stop new wallet creation)
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @notice Unpause factory
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    // ============ Wallet Management (Factory-as-Sardis) ============
    // SECURITY: The factory is set as the `sardis` address in deployed wallets.
    // Without these proxy functions, onlySardis wallet methods (setLimits, pause,
    // unpause, setRecoveryAddress, proposeSardisTransfer) would be uncallable,
    // making wallets unmanageable after deployment.

    /**
     * @notice Set spending limits on an agent wallet
     * @param wallet The wallet address to configure
     * @param _limitPerTx New per-transaction limit
     * @param _dailyLimit New daily limit
     * @param _coSignLimitPerTx New co-sign per-transaction limit
     * @param _coSignDailyLimit New co-sign daily limit
     */
    function setWalletLimits(
        address wallet,
        uint256 _limitPerTx,
        uint256 _dailyLimit,
        uint256 _coSignLimitPerTx,
        uint256 _coSignDailyLimit
    ) external onlyOwner {
        require(isValidWallet[wallet], "Not a Sardis wallet");
        SardisAgentWallet(payable(wallet)).setLimits(
            _limitPerTx, _dailyLimit, _coSignLimitPerTx, _coSignDailyLimit
        );
    }

    /**
     * @notice Pause an agent wallet (emergency stop)
     * @param wallet The wallet address to pause
     */
    function pauseWallet(address wallet) external onlyOwner {
        require(isValidWallet[wallet], "Not a Sardis wallet");
        SardisAgentWallet(payable(wallet)).pause();
    }

    /**
     * @notice Unpause an agent wallet
     * @param wallet The wallet address to unpause
     */
    function unpauseWallet(address wallet) external onlyOwner {
        require(isValidWallet[wallet], "Not a Sardis wallet");
        SardisAgentWallet(payable(wallet)).unpause();
    }

    /**
     * @notice Update recovery address on an agent wallet
     * @param wallet The wallet address
     * @param _recoveryAddress New recovery address
     */
    function setWalletRecoveryAddress(
        address wallet,
        address _recoveryAddress
    ) external onlyOwner {
        require(isValidWallet[wallet], "Not a Sardis wallet");
        SardisAgentWallet(payable(wallet)).setRecoveryAddress(_recoveryAddress);
    }

    /**
     * @notice Propose transfer of Sardis role from factory to a new address
     * @dev Step 1 of two-step timelock transfer. Used when migrating to a new
     *      factory or dedicated Sardis address.
     * @param wallet The wallet to transfer Sardis role on
     * @param _newSardis The proposed new Sardis address
     */
    function proposeWalletSardisTransfer(
        address wallet,
        address _newSardis
    ) external onlyOwner {
        require(isValidWallet[wallet], "Not a Sardis wallet");
        SardisAgentWallet(payable(wallet)).proposeSardisTransfer(_newSardis);
    }

    /**
     * @notice Execute a pending Sardis role transfer on a wallet
     * @param wallet The wallet to execute transfer on
     */
    function executeWalletSardisTransfer(address wallet) external onlyOwner {
        require(isValidWallet[wallet], "Not a Sardis wallet");
        SardisAgentWallet(payable(wallet)).executeSardisTransfer();
    }

    /**
     * @notice Toggle allowlist mode on a wallet
     * @param wallet The wallet to configure
     * @param _useAllowlist Whether to use allowlist mode
     */
    function setWalletAllowlistMode(
        address wallet,
        bool _useAllowlist
    ) external onlyOwner {
        require(isValidWallet[wallet], "Not a Sardis wallet");
        SardisAgentWallet(payable(wallet)).setAllowlistMode(_useAllowlist);
    }

    // ============ View Functions ============

    /**
     * @notice Get all wallets for an agent
     */
    function getAgentWallets(address agent) external view returns (address[] memory) {
        return agentWallets[agent];
    }
    
    /**
     * @notice Get wallet count for an agent
     */
    function getAgentWalletCount(address agent) external view returns (uint256) {
        return agentWallets[agent].length;
    }
    
    /**
     * @notice Get total number of deployed wallets
     */
    function getTotalWallets() external view returns (uint256) {
        return allWallets.length;
    }
    
    /**
     * @notice Check if a wallet is a valid Sardis wallet
     */
    function verifyWallet(address wallet) external view returns (bool) {
        return isValidWallet[wallet];
    }
    
    // ============ Receive ============
    
    receive() external payable {}
}

