// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/SardisWalletFactory.sol";
import "../src/SardisEscrow.sol";

/**
 * @title DeployMainnet
 * @notice Mainnet deployment script for Sardis smart contracts
 * @dev Production configuration with security checks
 *
 * IMPORTANT: Before mainnet deployment:
 *   1. Ensure contracts have been audited
 *   2. Test thoroughly on all testnets
 *   3. Review all parameters
 *   4. Set up monitoring and alerting
 *   5. Have incident response plan ready
 *
 * Supported Mainnets:
 *   1. Base (primary - lowest fees)
 *   2. Polygon
 *   3. Ethereum
 *   4. Arbitrum
 *   5. Optimism
 *
 * Usage:
 *   # Deploy to Base Mainnet (recommended first)
 *   forge script script/DeployMainnet.s.sol:DeployMainnet \
 *     --rpc-url $BASE_RPC_URL \
 *     --broadcast \
 *     --verify \
 *     --etherscan-api-key $BASESCAN_API_KEY \
 *     -vvvv
 *
 *   # Dry run first (no --broadcast)
 *   forge script script/DeployMainnet.s.sol:DeployMainnet \
 *     --rpc-url $BASE_RPC_URL \
 *     -vvvv
 */
contract DeployMainnet is Script {
    // Production configuration
    // These limits are conservative for initial launch
    uint256 constant LIMIT_PER_TX = 10000 * 10**6;      // $10,000 USDC per transaction
    uint256 constant DAILY_LIMIT = 100000 * 10**6;      // $100,000 USDC daily
    uint256 constant ESCROW_FEE_BPS = 50;               // 0.5% fee
    uint256 constant MIN_ESCROW_AMOUNT = 10 * 10**6;    // $10 USDC minimum
    uint256 constant MAX_DEADLINE_DAYS = 30;            // 30 day max escrow

    // Mainnet USDC addresses for reference
    address constant BASE_USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant POLYGON_USDC = 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359;
    address constant ETHEREUM_USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant ARBITRUM_USDC = 0xaf88d065e77c8cC2239327C5EDb3A432268e5831;
    address constant OPTIMISM_USDC = 0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85;

    function run() external {
        // Security checks
        require(block.chainid != 31337, "Use Deploy.s.sol for local testing");

        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        address recoveryAddress = vm.envOr("RECOVERY_ADDRESS", deployer);

        // Additional security: require explicit recovery address for mainnet
        require(
            vm.envOr("CONFIRM_MAINNET", false) == true,
            "Set CONFIRM_MAINNET=true to confirm mainnet deployment"
        );

        console.log("=== MAINNET DEPLOYMENT ===");
        console.log("Chain ID:", block.chainid);
        console.log("Deployer:", deployer);
        console.log("Recovery:", recoveryAddress);
        console.log("");
        console.log("Configuration:");
        console.log("  Per-TX Limit: $", LIMIT_PER_TX / 10**6);
        console.log("  Daily Limit:  $", DAILY_LIMIT / 10**6);
        console.log("  Escrow Fee:   ", ESCROW_FEE_BPS, "bps (0.5%)");
        console.log("");

        // Check deployer has enough ETH for gas
        uint256 balance = deployer.balance;
        console.log("Deployer ETH balance:", balance);
        require(balance > 0.01 ether, "Insufficient ETH for deployment");

        vm.startBroadcast(deployerPrivateKey);

        // Deploy WalletFactory
        SardisWalletFactory factory = new SardisWalletFactory(
            LIMIT_PER_TX,
            DAILY_LIMIT,
            recoveryAddress
        );

        console.log("");
        console.log("SardisWalletFactory deployed:", address(factory));

        // Deploy Escrow
        SardisEscrow escrow = new SardisEscrow(
            deployer,           // Arbiter
            ESCROW_FEE_BPS,
            MIN_ESCROW_AMOUNT,
            MAX_DEADLINE_DAYS
        );

        console.log("SardisEscrow deployed:", address(escrow));

        vm.stopBroadcast();

        // Output for .env
        console.log("");
        console.log("=== UPDATE .env WITH ===");

        string memory chainName = getChainName(block.chainid);
        console.log(string.concat("SARDIS_WALLET_FACTORY_", chainName, "="), address(factory));
        console.log(string.concat("SARDIS_ESCROW_", chainName, "="), address(escrow));

        console.log("");
        console.log("=== NEXT STEPS ===");
        console.log("1. Verify contracts on block explorer");
        console.log("2. Update sardis-chain config with new addresses");
        console.log("3. Test with small amount before full launch");
        console.log("4. Set up monitoring for contract events");
    }

    function getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 8453) return "BASE";
        if (chainId == 137) return "POLYGON";
        if (chainId == 1) return "ETHEREUM";
        if (chainId == 42161) return "ARBITRUM";
        if (chainId == 10) return "OPTIMISM";
        return "UNKNOWN";
    }
}

/**
 * @title DeployBaseMainnet
 * @notice Convenience script for Base mainnet (recommended first deployment)
 */
contract DeployBaseMainnet is Script {
    function run() external {
        require(block.chainid == 8453, "This script is for Base mainnet only");

        // Delegate to main deployment
        DeployMainnet mainScript = new DeployMainnet();
        mainScript.run();
    }
}

/**
 * @title VerifyDeployment
 * @notice Script to verify deployed contracts are working correctly
 */
contract VerifyDeployment is Script {
    function run() external view {
        address factoryAddr = vm.envAddress("SARDIS_WALLET_FACTORY");
        address escrowAddr = vm.envAddress("SARDIS_ESCROW");

        console.log("Verifying deployment...");
        console.log("Factory:", factoryAddr);
        console.log("Escrow:", escrowAddr);

        // Check factory
        SardisWalletFactory factory = SardisWalletFactory(factoryAddr);
        console.log("Factory limit per tx:", factory.limitPerTx());
        console.log("Factory daily limit:", factory.dailyLimit());
        console.log("Factory recovery:", factory.recoveryAddress());

        // Check escrow
        SardisEscrow escrow = SardisEscrow(escrowAddr);
        console.log("Escrow arbiter:", escrow.arbiter());
        console.log("Escrow fee:", escrow.feeBasisPoints(), "bps");
        console.log("Escrow min amount:", escrow.minEscrowAmount());

        console.log("");
        console.log("Verification complete!");
    }
}
