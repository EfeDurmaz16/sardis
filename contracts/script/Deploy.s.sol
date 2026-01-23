// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/SardisWalletFactory.sol";
import "../src/SardisEscrow.sol";

/**
 * @title Deploy
 * @notice Deployment script for Sardis smart contracts
 * @dev Supports deployment to all Sardis-supported testnets
 *
 * Supported Testnets (in deployment order):
 *   1. Base Sepolia (primary)
 *   2. Polygon Amoy
 *   3. Ethereum Sepolia
 *   4. Arbitrum Sepolia
 *   5. Optimism Sepolia
 *
 * Environment Variables Required:
 *   - PRIVATE_KEY: Deployer wallet private key
 *   - RECOVERY_ADDRESS: (optional) Recovery address, defaults to deployer
 *   - *_RPC_URL: RPC endpoint for each network
 *   - *_API_KEY: Block explorer API key for verification
 *
 * Usage:
 *   # Deploy to Base Sepolia (primary testnet)
 *   forge script script/Deploy.s.sol:Deploy --rpc-url base_sepolia --broadcast --verify
 *
 *   # Deploy to Polygon Amoy
 *   forge script script/Deploy.s.sol:Deploy --rpc-url polygon_amoy --broadcast --verify
 *
 *   # Deploy to Ethereum Sepolia
 *   forge script script/Deploy.s.sol:Deploy --rpc-url sepolia --broadcast --verify
 *
 *   # Deploy to Arbitrum Sepolia
 *   forge script script/Deploy.s.sol:Deploy --rpc-url arbitrum_sepolia --broadcast --verify
 *
 *   # Deploy to Optimism Sepolia
 *   forge script script/Deploy.s.sol:Deploy --rpc-url optimism_sepolia --broadcast --verify
 *
 *   # Deploy to local anvil (no verification)
 *   forge script script/Deploy.s.sol:Deploy --rpc-url localhost --broadcast
 *
 * After Deployment:
 *   Update contract addresses in packages/sardis-chain/src/sardis_chain/executor.py
 */
contract Deploy is Script {
    // Default configuration (can be overridden with env vars)
    uint256 constant DEFAULT_LIMIT_PER_TX = 1000 * 10**6;    // 1000 USDC (6 decimals)
    uint256 constant DEFAULT_DAILY_LIMIT = 10000 * 10**6;    // 10000 USDC
    uint256 constant ESCROW_FEE_BPS = 50;                     // 0.5% fee
    uint256 constant MIN_ESCROW_AMOUNT = 1 * 10**6;          // 1 USDC minimum
    uint256 constant MAX_DEADLINE_DAYS = 30;                  // 30 day max escrow

    function run() external {
        // Get deployer private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        
        // Get or set recovery address
        address recoveryAddress = vm.envOr("RECOVERY_ADDRESS", deployer);
        
        console.log("Deploying Sardis contracts...");
        console.log("Deployer:", deployer);
        console.log("Recovery Address:", recoveryAddress);
        
        vm.startBroadcast(deployerPrivateKey);
        
        // Deploy WalletFactory
        SardisWalletFactory factory = new SardisWalletFactory(
            DEFAULT_LIMIT_PER_TX,
            DEFAULT_DAILY_LIMIT,
            recoveryAddress
        );
        
        console.log("SardisWalletFactory deployed at:", address(factory));
        
        // Deploy Escrow
        SardisEscrow escrow = new SardisEscrow(
            deployer,           // Arbiter (Sardis)
            ESCROW_FEE_BPS,
            MIN_ESCROW_AMOUNT,
            MAX_DEADLINE_DAYS
        );
        
        console.log("SardisEscrow deployed at:", address(escrow));
        
        vm.stopBroadcast();
        
        // Output addresses for .env file
        console.log("\n=== Add to .env ===");
        console.log("SARDIS_WALLET_FACTORY=", address(factory));
        console.log("SARDIS_ESCROW=", address(escrow));
    }
}

/**
 * @title DeployTestnet
 * @notice Deploy with testnet-specific settings
 */
contract DeployTestnet is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        
        console.log("Deploying to testnet...");
        console.log("Deployer:", deployer);
        
        vm.startBroadcast(deployerPrivateKey);
        
        // Lower limits for testing
        SardisWalletFactory factory = new SardisWalletFactory(
            100 * 10**6,    // 100 USDC per tx
            1000 * 10**6,   // 1000 USDC daily
            deployer
        );
        
        SardisEscrow escrow = new SardisEscrow(
            deployer,
            100,            // 1% fee for testing visibility
            1 * 10**4,      // 0.01 USDC minimum
            7               // 7 day max deadline
        );
        
        vm.stopBroadcast();
        
        console.log("Factory:", address(factory));
        console.log("Escrow:", address(escrow));
    }
}

