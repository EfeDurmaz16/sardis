// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/SardisPolicyModule.sol";
import "../src/SardisLedgerAnchor.sol";
import "../src/SardisAgentRegistry.sol";

/**
 * @title DeploySafeModules
 * @notice Deployment script for Sardis contracts that work with Safe Smart Accounts
 * @dev Only deploys contracts WE own. Safe infrastructure (proxy factory, singleton,
 *      4337 module) is already deployed on all EVM chains — zero cost.
 *
 * Deployed contracts:
 *   1. SardisPolicyModule — Safe module for spending policy enforcement
 *   2. SardisLedgerAnchor — On-chain audit trail anchoring
 *   3. SardisAgentRegistry — Agent identity registry (Base mainnet initially)
 *
 * Environment Variables Required:
 *   - PRIVATE_KEY: Deployer wallet private key
 *   - SARDIS_ADDRESS: Sardis platform address (admin for PolicyModule)
 *   - DEPLOY_REGISTRY: Set to "1" to also deploy AgentRegistry (optional)
 *
 * Usage:
 *   # Deploy PolicyModule + LedgerAnchor to Base Sepolia
 *   forge script script/DeploySafeModules.s.sol:DeploySafeModules \
 *     --rpc-url base_sepolia --broadcast --verify
 *
 *   # Deploy all contracts including AgentRegistry
 *   DEPLOY_REGISTRY=1 forge script script/DeploySafeModules.s.sol:DeploySafeModules \
 *     --rpc-url base --broadcast --verify
 */
contract DeploySafeModules is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address sardisAddress = vm.envAddress("SARDIS_ADDRESS");
        bool deployRegistry = vm.envOr("DEPLOY_REGISTRY", false);

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy SardisPolicyModule
        SardisPolicyModule policyModule = new SardisPolicyModule(sardisAddress);
        console.log("SardisPolicyModule deployed at:", address(policyModule));

        // 2. Deploy SardisLedgerAnchor
        SardisLedgerAnchor ledgerAnchor = new SardisLedgerAnchor();
        console.log("SardisLedgerAnchor deployed at:", address(ledgerAnchor));

        // 3. Optionally deploy SardisAgentRegistry
        if (deployRegistry) {
            SardisAgentRegistry agentRegistry = new SardisAgentRegistry();
            console.log("SardisAgentRegistry deployed at:", address(agentRegistry));
        }

        vm.stopBroadcast();
    }
}
