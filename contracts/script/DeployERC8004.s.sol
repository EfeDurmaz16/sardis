// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/SardisIdentityRegistry.sol";
import "../src/SardisReputationRegistry.sol";
import "../src/SardisValidationRegistry.sol";

/**
 * @title DeployERC8004
 * @notice Deployment script for Sardis ERC-8004 agent identity infrastructure
 * @dev Deploys the full ERC-8004 stack in dependency order:
 *      1. SardisIdentityRegistry — ERC-721 agent identity (must deploy first)
 *      2. SardisReputationRegistry — on-chain feedback linked to identity
 *      3. SardisValidationRegistry — validator assessments linked to identity
 *
 * Environment Variables Required:
 *   - PRIVATE_KEY: Deployer wallet private key
 *
 * Usage:
 *   # Deploy to Base Sepolia
 *   forge script script/DeployERC8004.s.sol:DeployERC8004 \
 *     --rpc-url base_sepolia --broadcast --verify
 *
 *   # Deploy to Base mainnet
 *   forge script script/DeployERC8004.s.sol:DeployERC8004 \
 *     --rpc-url base --broadcast --verify
 */
contract DeployERC8004 is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy SardisIdentityRegistry (ERC-721 based)
        SardisIdentityRegistry identityRegistry = new SardisIdentityRegistry();
        console.log("SardisIdentityRegistry deployed at:", address(identityRegistry));

        // 2. Deploy SardisReputationRegistry (linked to identity)
        SardisReputationRegistry reputationRegistry = new SardisReputationRegistry(address(identityRegistry));
        console.log("SardisReputationRegistry deployed at:", address(reputationRegistry));

        // 3. Deploy SardisValidationRegistry (linked to identity)
        SardisValidationRegistry validationRegistry = new SardisValidationRegistry(address(identityRegistry));
        console.log("SardisValidationRegistry deployed at:", address(validationRegistry));

        vm.stopBroadcast();

        // Summary
        console.log("");
        console.log("========== ERC-8004 Deployment Summary ==========");
        console.log("  SardisIdentityRegistry:    ", address(identityRegistry));
        console.log("  SardisReputationRegistry:  ", address(reputationRegistry));
        console.log("  SardisValidationRegistry:  ", address(validationRegistry));
        console.log("=================================================");
    }
}
