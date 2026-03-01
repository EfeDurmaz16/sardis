// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/SardisPolicyModule.sol";
import "../src/SardisLedgerAnchor.sol";
import "../src/RefundProtocol.sol";

/**
 * @title DeploySafeModules
 * @notice Deployment script for Sardis contracts that work with Safe Smart Accounts
 * @dev Only deploys contracts WE own. All other infrastructure is pre-deployed:
 *      - Safe (proxy factory, singleton, 4337 module) — all EVM chains
 *      - EAS (agent identity/attestation) — all EVM chains
 *      - Permit2 (token approvals) — all EVM chains
 *
 * Deployed contracts:
 *   1. SardisPolicyModule — Safe module for spending policy enforcement
 *   2. SardisLedgerAnchor — On-chain audit trail anchoring
 *   3. RefundProtocol — Circle's audited escrow (Apache 2.0)
 *
 * Environment Variables Required:
 *   - PRIVATE_KEY: Deployer wallet private key
 *   - SARDIS_ADDRESS: Sardis platform address (admin for PolicyModule)
 *   - USDC_ADDRESS: USDC token address on target chain
 *
 * Usage:
 *   # Deploy to Base Sepolia
 *   forge script script/DeploySafeModules.s.sol:DeploySafeModules \
 *     --rpc-url base_sepolia --broadcast --verify
 *
 *   # Deploy to Base mainnet
 *   forge script script/DeploySafeModules.s.sol:DeploySafeModules \
 *     --rpc-url base --broadcast --verify
 */
contract DeploySafeModules is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address sardisAddress = vm.envAddress("SARDIS_ADDRESS");
        address usdcAddress = vm.envAddress("USDC_ADDRESS");

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy SardisPolicyModule
        SardisPolicyModule policyModule = new SardisPolicyModule(sardisAddress);
        console.log("SardisPolicyModule deployed at:", address(policyModule));

        // 2. Deploy SardisLedgerAnchor
        SardisLedgerAnchor ledgerAnchor = new SardisLedgerAnchor();
        console.log("SardisLedgerAnchor deployed at:", address(ledgerAnchor));

        // 3. Deploy Circle RefundProtocol (audited escrow)
        // Sardis deployer becomes the arbiter for dispute resolution
        RefundProtocol refundProtocol = new RefundProtocol(
            sardisAddress,  // arbiter
            usdcAddress,    // USDC
            "RefundProtocol",
            "1"
        );
        console.log("RefundProtocol deployed at:", address(refundProtocol));

        vm.stopBroadcast();

        // Pre-deployed infrastructure (no deployment needed):
        console.log("");
        console.log("Pre-deployed infrastructure (already on all chains):");
        console.log("  Safe ProxyFactory:  0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2");
        console.log("  Safe Singleton:     0x41675C099F32341bf84BFc5382aF534df5C7461a");
        console.log("  Safe 4337 Module:   0x75cf11467937ce3F2f357CE24ffc3DBF8fD5c226");
        console.log("  Permit2:            0x000000000022D473030F116dDEE9F6B43aC78BA3");
        console.log("  EAS:                See eas_registry.py for per-chain addresses");
    }
}
