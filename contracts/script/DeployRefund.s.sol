// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/RefundProtocol.sol";

contract DeployRefund is Script {
    function run() external {
        vm.startBroadcast();
        new RefundProtocol(
            0x25b6C401B0b2B35E1f9d2970EebFDc941E5AaFD8,
            0x20C000000000000000000000b9537d11c60E8b50,
            "SardisRefund",
            "1"
        );
        vm.stopBroadcast();
    }
}
