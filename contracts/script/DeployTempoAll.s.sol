// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/SardisIdentityRegistry.sol";
import "../src/SardisJobRegistry.sol";
import "../src/SardisJobManager.sol";
import "../src/SardisReputationRegistry.sol";
import "../src/SardisValidationRegistry.sol";

contract DeployTempoAll is Script {
    function run() external {
        address deployer = msg.sender;
        uint256 feeBps = 100; // 1% platform fee

        vm.startBroadcast();

        // 1. Identity Registry (no args — ERC-721 agent identities)
        SardisIdentityRegistry identityRegistry = new SardisIdentityRegistry();

        // 2. Job Registry (owner = deployer)
        SardisJobRegistry jobRegistry = new SardisJobRegistry(deployer);

        // 3. Job Manager (owner, feeRecipient = deployer, 1% fee)
        SardisJobManager jobManager = new SardisJobManager(deployer, deployer, feeBps);

        // 4. Reputation Registry (linked to identity registry)
        SardisReputationRegistry reputationRegistry = new SardisReputationRegistry(address(identityRegistry));

        // 5. Validation Registry (linked to identity registry)
        SardisValidationRegistry validationRegistry = new SardisValidationRegistry(address(identityRegistry));

        vm.stopBroadcast();
    }
}
