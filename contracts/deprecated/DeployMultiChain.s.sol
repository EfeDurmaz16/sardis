// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/StdJson.sol";
import "../src/SardisWalletFactory.sol";
import "../src/SardisEscrow.sol";

/**
 * @title DeployMultiChain
 * @notice Multi-chain deployment script for Sardis smart contracts
 * @dev Deploys to all supported chains and outputs deployment addresses to JSON
 *
 * Supported Chains:
 *   Testnets: Base Sepolia, Polygon Amoy, Ethereum Sepolia, Arbitrum Sepolia, Optimism Sepolia
 *   Mainnets: Base, Polygon, Ethereum, Arbitrum, Optimism (requires audit first)
 *
 * Environment Variables:
 *   - PRIVATE_KEY: Deployer wallet private key
 *   - RECOVERY_ADDRESS: (optional) Recovery address for wallet factory
 *
 * Usage:
 *   # Deploy to single chain
 *   forge script script/DeployMultiChain.s.sol:DeployMultiChain --rpc-url base_sepolia --broadcast --verify
 *
 *   # Run deployment simulation (no broadcast)
 *   forge script script/DeployMultiChain.s.sol:DeployMultiChain --rpc-url base_sepolia
 */
contract DeployMultiChain is Script {
    using stdJson for string;

    // Deployment configuration
    struct DeployConfig {
        uint256 limitPerTx;
        uint256 dailyLimit;
        uint256 escrowFeeBps;
        uint256 minEscrowAmount;
        uint256 maxDeadlineDays;
    }

    // Deployment result
    struct Deployment {
        address walletFactory;
        address escrow;
        uint256 chainId;
        uint256 blockNumber;
        uint256 timestamp;
    }

    // Chain name to config mapping
    mapping(uint256 => string) public chainNames;

    // Testnet configuration (lower limits)
    DeployConfig public testnetConfig = DeployConfig({
        limitPerTx: 100 * 10**6,      // 100 USDC
        dailyLimit: 1000 * 10**6,     // 1000 USDC
        escrowFeeBps: 100,            // 1% for visibility
        minEscrowAmount: 1 * 10**4,   // 0.01 USDC
        maxDeadlineDays: 7            // 7 days
    });

    // Mainnet configuration (production limits)
    DeployConfig public mainnetConfig = DeployConfig({
        limitPerTx: 10000 * 10**6,    // 10000 USDC
        dailyLimit: 100000 * 10**6,   // 100000 USDC
        escrowFeeBps: 50,             // 0.5%
        minEscrowAmount: 1 * 10**6,   // 1 USDC
        maxDeadlineDays: 30           // 30 days
    });

    constructor() {
        // Testnets
        chainNames[84532] = "base_sepolia";
        chainNames[80002] = "polygon_amoy";
        chainNames[11155111] = "ethereum_sepolia";
        chainNames[421614] = "arbitrum_sepolia";
        chainNames[11155420] = "optimism_sepolia";

        // Mainnets
        chainNames[8453] = "base";
        chainNames[137] = "polygon";
        chainNames[1] = "ethereum";
        chainNames[42161] = "arbitrum";
        chainNames[10] = "optimism";
    }

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        address recoveryAddress = vm.envOr("RECOVERY_ADDRESS", deployer);

        uint256 chainId = block.chainid;
        string memory chainName = chainNames[chainId];

        require(bytes(chainName).length > 0, "Unsupported chain");

        bool isMainnet = isMainnetChain(chainId);
        DeployConfig memory config = isMainnet ? mainnetConfig : testnetConfig;

        console.log("=== Sardis Multi-Chain Deployment ===");
        console.log("Chain:", chainName);
        console.log("Chain ID:", chainId);
        console.log("Deployer:", deployer);
        console.log("Recovery:", recoveryAddress);
        console.log("Is Mainnet:", isMainnet);
        console.log("");

        if (isMainnet) {
            console.log("WARNING: Deploying to MAINNET!");
            console.log("Ensure contracts have been audited before proceeding.");
            console.log("");
        }

        vm.startBroadcast(deployerPrivateKey);

        // Deploy WalletFactory
        SardisWalletFactory factory = new SardisWalletFactory(
            config.limitPerTx,
            config.dailyLimit,
            recoveryAddress
        );

        console.log("SardisWalletFactory:", address(factory));

        // Deploy Escrow
        SardisEscrow escrow = new SardisEscrow(
            deployer,
            config.escrowFeeBps,
            config.minEscrowAmount,
            config.maxDeadlineDays
        );

        console.log("SardisEscrow:", address(escrow));

        vm.stopBroadcast();

        // Create deployment record
        Deployment memory deployment = Deployment({
            walletFactory: address(factory),
            escrow: address(escrow),
            chainId: chainId,
            blockNumber: block.number,
            timestamp: block.timestamp
        });

        // Output deployment JSON
        outputDeploymentJson(chainName, deployment, deployer);
    }

    function isMainnetChain(uint256 chainId) internal pure returns (bool) {
        return chainId == 8453 ||   // Base
               chainId == 137 ||    // Polygon
               chainId == 1 ||      // Ethereum
               chainId == 42161 ||  // Arbitrum
               chainId == 10;       // Optimism
    }

    function outputDeploymentJson(
        string memory chainName,
        Deployment memory deployment,
        address deployer
    ) internal view {
        string memory json = string(abi.encodePacked(
            '{\n',
            '  "chain": "', chainName, '",\n',
            '  "chainId": ', vm.toString(deployment.chainId), ',\n',
            '  "deployer": "', vm.toString(deployer), '",\n',
            '  "contracts": {\n',
            '    "walletFactory": "', vm.toString(deployment.walletFactory), '",\n',
            '    "escrow": "', vm.toString(deployment.escrow), '"\n',
            '  },\n',
            '  "blockNumber": ', vm.toString(deployment.blockNumber), ',\n',
            '  "timestamp": ', vm.toString(deployment.timestamp), '\n',
            '}'
        ));

        console.log("\n=== Deployment JSON ===");
        console.log(json);
        console.log("\n=== Environment Variables ===");
        console.log(string(abi.encodePacked(
            "SARDIS_", toUpperCase(chainName), "_WALLET_FACTORY_ADDRESS=",
            vm.toString(deployment.walletFactory)
        )));
        console.log(string(abi.encodePacked(
            "SARDIS_", toUpperCase(chainName), "_ESCROW_ADDRESS=",
            vm.toString(deployment.escrow)
        )));
    }

    function toUpperCase(string memory str) internal pure returns (string memory) {
        bytes memory bStr = bytes(str);
        bytes memory bUpper = new bytes(bStr.length);
        for (uint i = 0; i < bStr.length; i++) {
            if ((uint8(bStr[i]) >= 97) && (uint8(bStr[i]) <= 122)) {
                bUpper[i] = bytes1(uint8(bStr[i]) - 32);
            } else {
                bUpper[i] = bStr[i];
            }
        }
        return string(bUpper);
    }
}

/**
 * @title DeployAllTestnets
 * @notice Batch deployment to all testnets (run with --multi flag)
 * @dev Use with: forge script script/DeployMultiChain.s.sol:DeployAllTestnets --broadcast --multi
 */
contract DeployAllTestnets is Script {
    function run() external {
        // This script is meant to be run with --multi flag
        // which will execute against all configured RPC URLs

        console.log("=== Deploy All Testnets ===");
        console.log("Run with --multi flag to deploy to all testnets");
        console.log("");
        console.log("Example:");
        console.log("  forge script script/DeployMultiChain.s.sol:DeployMultiChain --broadcast --multi");
        console.log("");
        console.log("Configure RPC URLs in foundry.toml:");
        console.log("  [rpc_endpoints]");
        console.log("  base_sepolia = \"https://sepolia.base.org\"");
        console.log("  polygon_amoy = \"https://rpc-amoy.polygon.technology\"");
        console.log("  ...");
    }
}
