// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/SardisSmartAccountFactory.sol";
import "../src/SardisVerifyingPaymaster.sol";

/**
 * @title DeployERC4337BaseSepolia
 * @notice Deploy ERC-4337 smart wallet contracts on Base Sepolia.
 */
contract DeployERC4337BaseSepolia is Script {
    address constant ENTRYPOINT_V07 = 0x0000000071727De22E5E9d8BAf0edAc6f37da032;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        uint256 maxSponsoredCostPerOp = vm.envOr("SARDIS_PAYMASTER_MAX_COST_PER_OP", uint256(0.02 ether));
        uint256 dailySponsorCap = vm.envOr("SARDIS_PAYMASTER_DAILY_CAP", uint256(1 ether));

        vm.startBroadcast(deployerPrivateKey);

        SardisSmartAccountFactory factory = new SardisSmartAccountFactory(ENTRYPOINT_V07, deployer);
        SardisVerifyingPaymaster paymaster = new SardisVerifyingPaymaster(
            ENTRYPOINT_V07,
            deployer,
            maxSponsoredCostPerOp,
            dailySponsorCap
        );

        vm.stopBroadcast();

        console.log("SardisSmartAccountFactory:", address(factory));
        console.log("SardisVerifyingPaymaster:", address(paymaster));
        console.log("EntryPoint v0.7:", ENTRYPOINT_V07);
    }
}
