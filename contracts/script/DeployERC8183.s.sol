// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/SardisJobManager.sol";
import "../src/SardisJobRegistry.sol";
import "../src/hooks/SardisTrustHook.sol";
import "../src/hooks/SardisReputationHook.sol";

/**
 * @title DeployERC8183
 * @notice Deployment script for Sardis ERC-8183 job infrastructure
 * @dev Deploys the full ERC-8183 stack in dependency order:
 *      1. SardisJobRegistry — on-chain reputation store
 *      2. SardisJobManager — core job escrow and lifecycle
 *      3. SardisTrustHook — trust-gated lifecycle transitions
 *      4. SardisReputationHook — auto-writes reputation on lifecycle events
 *      Then wires up permissions and configuration.
 *
 * Environment Variables Required:
 *   - PRIVATE_KEY: Deployer wallet private key
 *   - USDC_ADDRESS: USDC token address on target chain
 *   - FEE_RECIPIENT: Address to receive protocol fees
 *
 * Optional:
 *   - FEE_BPS: Fee in basis points (default: 100 = 1%, max: 500 = 5%)
 *   - MIN_CLIENT_TRUST: Min client trust score for TrustHook (default: 0 = disabled)
 *   - MIN_PROVIDER_JOBS: Min provider completed jobs for TrustHook (default: 0 = disabled)
 *   - MIN_EVALUATOR_TRUST: Min evaluator trust score for TrustHook (default: 0 = disabled)
 *
 * Usage:
 *   # Deploy to Base Sepolia
 *   forge script script/DeployERC8183.s.sol:DeployERC8183 \
 *     --rpc-url base_sepolia --broadcast --verify
 *
 *   # Deploy to Base mainnet
 *   forge script script/DeployERC8183.s.sol:DeployERC8183 \
 *     --rpc-url base --broadcast --verify
 */
contract DeployERC8183 is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        address usdcAddress = vm.envAddress("USDC_ADDRESS");
        address feeRecipientAddr = vm.envAddress("FEE_RECIPIENT");
        uint256 feeBps = vm.envOr("FEE_BPS", uint256(100));
        uint256 minClientTrust = vm.envOr("MIN_CLIENT_TRUST", uint256(0));
        uint256 minProviderJobs = vm.envOr("MIN_PROVIDER_JOBS", uint256(0));
        uint256 minEvaluatorTrust = vm.envOr("MIN_EVALUATOR_TRUST", uint256(0));

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy SardisJobRegistry
        SardisJobRegistry registry = new SardisJobRegistry(deployer);
        console.log("SardisJobRegistry deployed at:", address(registry));

        // 2. Deploy SardisJobManager
        SardisJobManager jobManager = new SardisJobManager(deployer, feeRecipientAddr, feeBps);
        console.log("SardisJobManager deployed at:", address(jobManager));

        // 3. Deploy SardisTrustHook (IACPHook compliant)
        SardisTrustHook trustHook = new SardisTrustHook(
            address(registry), address(jobManager), deployer, minClientTrust, minProviderJobs, minEvaluatorTrust
        );
        console.log("SardisTrustHook deployed at:", address(trustHook));

        // 4. Deploy SardisReputationHook
        SardisReputationHook reputationHook = new SardisReputationHook(address(registry), address(jobManager));
        console.log("SardisReputationHook deployed at:", address(reputationHook));

        // 5. Wire permissions: authorize the reputation hook to write to registry
        registry.setAuthorizedWriter(address(reputationHook), true);
        console.log("ReputationHook authorized as registry writer");

        // 6. Allow USDC on the job manager
        jobManager.setAllowedToken(usdcAddress, true);
        console.log("USDC allowed on JobManager:", usdcAddress);

        vm.stopBroadcast();

        // Summary
        console.log("");
        console.log("========== ERC-8183 Deployment Summary ==========");
        console.log("  SardisJobRegistry:      ", address(registry));
        console.log("  SardisJobManager:       ", address(jobManager));
        console.log("  SardisTrustHook:        ", address(trustHook));
        console.log("  SardisReputationHook:   ", address(reputationHook));
        console.log("  Fee BPS:                ", feeBps);
        console.log("  Fee Recipient:          ", feeRecipientAddr);
        console.log("  USDC:                   ", usdcAddress);
        console.log("=================================================");
    }
}
