// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/SardisWalletFactory.sol";
import "../src/SardisLedgerAnchor.sol";
import "../src/SardisAgentRegistry.sol";
import "../src/SardisEscrow.sol";

/**
 * @title DeployPhase1
 * @notice Phase 1 mainnet deployment — low-risk contracts only (no audit required)
 * @dev Deploys: WalletFactory, LedgerAnchor, AgentRegistry
 *      Skips:   SardisEscrow (needs audit), SardisVerifyingPaymaster (use Circle Paymaster)
 *
 * Strategy:
 *   - Circle Paymaster handles gas abstraction (permissionless, no deploy needed)
 *   - Off-chain escrow via DB-backed holds replaces SardisEscrow for Phase 1
 *   - SardisEscrow + custom Paymaster deferred to Phase 2 (post-audit)
 *
 * Usage:
 *   # Dry run first
 *   forge script script/DeployMainnet.s.sol:DeployPhase1 \
 *     --rpc-url $BASE_RPC_URL -vvvv
 *
 *   # Deploy to Base Mainnet
 *   forge script script/DeployMainnet.s.sol:DeployPhase1 \
 *     --rpc-url $BASE_RPC_URL \
 *     --broadcast --verify \
 *     --etherscan-api-key $BASESCAN_API_KEY \
 *     -vvvv
 */
contract DeployPhase1 is Script {
    // Production configuration — conservative for initial launch
    uint256 constant LIMIT_PER_TX = 10000 * 10**6;   // $10,000 USDC per transaction
    uint256 constant DAILY_LIMIT = 100000 * 10**6;    // $100,000 USDC daily

    // Mainnet USDC addresses
    address constant BASE_USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant POLYGON_USDC = 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359;
    address constant ETHEREUM_USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant ARBITRUM_USDC = 0xaf88d065e77c8cC2239327C5EDb3A432268e5831;
    address constant OPTIMISM_USDC = 0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85;

    function run() external {
        require(block.chainid != 31337, "Use Deploy.s.sol for local testing");

        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        address recoveryAddress = vm.envOr("RECOVERY_ADDRESS", deployer);

        require(
            vm.envOr("CONFIRM_MAINNET", false) == true,
            "Set CONFIRM_MAINNET=true to confirm mainnet deployment"
        );

        console.log("=== PHASE 1 MAINNET DEPLOYMENT ===");
        console.log("Chain ID:", block.chainid);
        console.log("Deployer:", deployer);
        console.log("Recovery:", recoveryAddress);
        console.log("");
        console.log("Contracts to deploy:");
        console.log("  [1] SardisWalletFactory  — agent wallet creation");
        console.log("  [2] SardisLedgerAnchor   — audit log anchoring");
        console.log("  [3] SardisAgentRegistry   — ERC-8004 agent identity");
        console.log("");
        console.log("NOT deploying (Phase 2):");
        console.log("  [ ] SardisEscrow          — using off-chain escrow");
        console.log("  [ ] SardisPaymaster       — using Circle Paymaster");
        console.log("");

        uint256 balance = deployer.balance;
        console.log("Deployer ETH balance:", balance);
        require(balance > 0.01 ether, "Insufficient ETH for deployment");

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy WalletFactory
        SardisWalletFactory factory = new SardisWalletFactory(
            LIMIT_PER_TX,
            DAILY_LIMIT,
            recoveryAddress
        );
        console.log("[1/3] SardisWalletFactory:", address(factory));

        // 2. Deploy LedgerAnchor
        SardisLedgerAnchor anchor = new SardisLedgerAnchor();
        console.log("[2/3] SardisLedgerAnchor: ", address(anchor));

        // 3. Deploy AgentRegistry
        SardisAgentRegistry registry = new SardisAgentRegistry();
        console.log("[3/3] SardisAgentRegistry:", address(registry));

        vm.stopBroadcast();

        // Output env vars
        string memory chainName = _getChainName(block.chainid);

        console.log("");
        console.log("=== UPDATE .env WITH ===");
        console.log(string.concat("SARDIS_WALLET_FACTORY_", chainName, "="), address(factory));
        console.log(string.concat("SARDIS_LEDGER_ANCHOR_", chainName, "="), address(anchor));
        console.log(string.concat("SARDIS_AGENT_REGISTRY_", chainName, "="), address(registry));

        console.log("");
        console.log("=== CIRCLE PAYMASTER (no deploy needed, permissionless) ===");
        console.log("CIRCLE_PAYMASTER=0x0578cFB241215b77442a541325d6A4E6dFE700Ec (all chains)");

        console.log("");
        console.log("=== NEXT STEPS ===");
        console.log("1. Verify contracts on block explorer (auto if --verify passed)");
        console.log("2. Update sardis-chain config with new addresses");
        console.log("3. Set SARDIS_PAYMASTER_PROVIDER=circle in .env");
        console.log("4. Test wallet creation with small amount");
        console.log("5. Set up monitoring for contract events");
    }

    function _getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 8453) return "BASE";
        if (chainId == 137) return "POLYGON";
        if (chainId == 1) return "ETHEREUM";
        if (chainId == 42161) return "ARBITRUM";
        if (chainId == 10) return "OPTIMISM";
        return "UNKNOWN";
    }
}

/**
 * @title DeployPhase2
 * @notice Phase 2 deployment — Circle RefundProtocol (audited escrow replacement)
 * @dev Replaces custom SardisEscrow with Circle's Apache 2.0 audited RefundProtocol.
 *      Sardis deployer becomes the arbiter for dispute resolution.
 *
 * Usage:
 *   forge script script/DeployMainnet.s.sol:DeployPhase2 \
 *     --rpc-url $BASE_RPC_URL \
 *     --broadcast --verify \
 *     --etherscan-api-key $BASESCAN_API_KEY \
 *     -vvvv
 */
contract DeployPhase2 is Script {

    function run() external {
        require(block.chainid != 31337, "Use Deploy.s.sol for local testing");

        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        require(
            vm.envOr("CONFIRM_MAINNET", false) == true,
            "Set CONFIRM_MAINNET=true to confirm mainnet deployment"
        );

        console.log("=== PHASE 2 MAINNET DEPLOYMENT ===");
        console.log("Circle RefundProtocol (audited escrow)");
        console.log("Chain ID:", block.chainid);
        console.log("Deployer / Arbiter:", deployer);

        uint256 balance = deployer.balance;
        require(balance > 0.01 ether, "Insufficient ETH for deployment");

        console.log("");
        console.log("NOTE: Deploy Circle RefundProtocol from circlefin/refund-protocol repo.");
        console.log("Sardis deployer address will be set as the _arbiter parameter.");
        console.log("");
        console.log("After deployment, update .env with:");

        string memory chainName = _getChainName(block.chainid);
        console.log(string.concat("  SARDIS_REFUND_PROTOCOL_", chainName, "=<deployed_address>"));
        console.log(string.concat("  SARDIS_ARBITER_", chainName, "="), deployer);
    }

    function _getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 8453) return "BASE";
        if (chainId == 137) return "POLYGON";
        if (chainId == 1) return "ETHEREUM";
        if (chainId == 42161) return "ARBITRUM";
        if (chainId == 10) return "OPTIMISM";
        return "UNKNOWN";
    }
}

/**
 * @title VerifyPhase1
 * @notice Verify Phase 1 deployed contracts are working correctly
 */
contract VerifyPhase1 is Script {
    function run() external view {
        address factoryAddr = vm.envAddress("SARDIS_WALLET_FACTORY");
        address anchorAddr = vm.envAddress("SARDIS_LEDGER_ANCHOR");
        address registryAddr = vm.envAddress("SARDIS_AGENT_REGISTRY");

        console.log("=== VERIFYING PHASE 1 DEPLOYMENT ===");

        // Check factory
        SardisWalletFactory factory = SardisWalletFactory(payable(factoryAddr));
        console.log("WalletFactory:", factoryAddr);
        console.log("  limit per tx:", factory.defaultLimitPerTx());
        console.log("  daily limit: ", factory.defaultDailyLimit());
        console.log("  recovery:    ", factory.defaultRecoveryAddress());
        console.log("  owner:       ", factory.owner());

        // Check anchor
        SardisLedgerAnchor anchor = SardisLedgerAnchor(anchorAddr);
        console.log("LedgerAnchor:", anchorAddr);
        console.log("  owner:", anchor.owner());

        // Check registry
        SardisAgentRegistry registry = SardisAgentRegistry(registryAddr);
        console.log("AgentRegistry:", registryAddr);
        console.log("  owner:", registry.owner());
        console.log("  name: ", registry.name());
        console.log("  symbol:", registry.symbol());

        console.log("");
        console.log("Phase 1 verification complete!");
    }
}
