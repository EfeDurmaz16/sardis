// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SardisIdentityRegistry.sol";
import "../src/interfaces/IIdentityRegistry.sol";

contract SardisIdentityRegistryTest is Test {
    SardisIdentityRegistry internal registry;

    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);
    address internal carol = address(0xCA401);

    uint256 internal walletPrivateKey = 0xBEEF;
    address internal walletAddress;

    function setUp() public {
        registry = new SardisIdentityRegistry();
        walletAddress = vm.addr(walletPrivateKey);
    }

    // ============ Register (3 overloads) ============

    function testRegisterWithURIAndMetadata() public {
        IIdentityRegistry.MetadataEntry[] memory meta = new IIdentityRegistry.MetadataEntry[](2);
        meta[0] = IIdentityRegistry.MetadataEntry("name", abi.encode("TestAgent"));
        meta[1] = IIdentityRegistry.MetadataEntry("version", abi.encode("1.0"));

        vm.prank(alice);
        uint256 agentId = registry.register("https://example.com/agent.json", meta);

        assertEq(agentId, 0);
        assertEq(registry.ownerOf(0), alice);
        assertEq(registry.tokenURI(0), "https://example.com/agent.json");
        assertEq(registry.getAgentWallet(0), alice); // Default wallet = owner
    }

    function testRegisterWithURIOnly() public {
        vm.prank(alice);
        uint256 agentId = registry.register("https://example.com/agent.json");

        assertEq(agentId, 0);
        assertEq(registry.ownerOf(0), alice);
    }

    function testRegisterBare() public {
        vm.prank(alice);
        uint256 agentId = registry.register();

        assertEq(agentId, 0);
        assertEq(registry.ownerOf(0), alice);
    }

    function testRegisterIncrements() public {
        vm.startPrank(alice);
        uint256 id0 = registry.register();
        uint256 id1 = registry.register("uri");
        vm.stopPrank();

        assertEq(id0, 0);
        assertEq(id1, 1);
        assertEq(registry.nextAgentId(), 2);
    }

    function testRegisterEmitsEvent() public {
        vm.prank(alice);
        vm.expectEmit(true, true, false, true);
        emit IIdentityRegistry.Registered(0, "https://test.com", alice);
        registry.register("https://test.com");
    }

    // ============ Metadata ============

    function testSetAndGetMetadata() public {
        vm.startPrank(alice);
        registry.register();
        registry.setMetadata(0, "skill", abi.encode("payment"));
        vm.stopPrank();

        bytes memory val = registry.getMetadata(0, "skill");
        assertEq(abi.decode(val, (string)), "payment");
    }

    function testSetMetadataRevertsReservedKey() public {
        vm.startPrank(alice);
        registry.register();

        vm.expectRevert(SardisIdentityRegistry.ReservedMetadataKey.selector);
        registry.setMetadata(0, "agentWallet", abi.encode(address(0x1)));
        vm.stopPrank();
    }

    function testRegisterMetadataRevertsReservedKey() public {
        IIdentityRegistry.MetadataEntry[] memory meta = new IIdentityRegistry.MetadataEntry[](1);
        meta[0] = IIdentityRegistry.MetadataEntry("agentWallet", abi.encode(address(0x1)));

        vm.prank(alice);
        vm.expectRevert(SardisIdentityRegistry.ReservedMetadataKey.selector);
        registry.register("uri", meta);
    }

    function testSetMetadataRevertsNotOwner() public {
        vm.prank(alice);
        registry.register();

        vm.prank(bob);
        vm.expectRevert(SardisIdentityRegistry.NotAgentOwnerOrApproved.selector);
        registry.setMetadata(0, "skill", abi.encode("x"));
    }

    function testMetadataEmitsEvent() public {
        vm.startPrank(alice);
        registry.register();

        vm.expectEmit(true, false, false, true);
        emit IIdentityRegistry.MetadataSet(0, "skill", "skill", abi.encode("pay"));
        registry.setMetadata(0, "skill", abi.encode("pay"));
        vm.stopPrank();
    }

    // ============ Agent URI ============

    function testSetAgentURI() public {
        vm.startPrank(alice);
        registry.register("old-uri");
        registry.setAgentURI(0, "new-uri");
        vm.stopPrank();

        assertEq(registry.tokenURI(0), "new-uri");
    }

    function testSetAgentURIRevertsNotOwner() public {
        vm.prank(alice);
        registry.register("uri");

        vm.prank(bob);
        vm.expectRevert(SardisIdentityRegistry.NotAgentOwnerOrApproved.selector);
        registry.setAgentURI(0, "hacked");
    }

    function testSetAgentURIEmitsEvent() public {
        vm.startPrank(alice);
        registry.register("uri");

        vm.expectEmit(true, true, false, true);
        emit IIdentityRegistry.URIUpdated(0, "new-uri", alice);
        registry.setAgentURI(0, "new-uri");
        vm.stopPrank();
    }

    // ============ Agent Wallet (EIP-712) ============

    function testSetAgentWallet() public {
        vm.prank(alice);
        registry.register();

        // Sign with walletPrivateKey
        bytes32 structHash = keccak256(
            abi.encode(
                keccak256("SetAgentWallet(uint256 agentId,address newWallet,uint256 deadline)"),
                0,
                walletAddress,
                block.timestamp + 1 hours
            )
        );
        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", registry.DOMAIN_SEPARATOR(), structHash)
        );
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(walletPrivateKey, digest);
        bytes memory sig = abi.encodePacked(r, s, v);

        vm.prank(alice);
        registry.setAgentWallet(0, walletAddress, block.timestamp + 1 hours, sig);

        assertEq(registry.getAgentWallet(0), walletAddress);
    }

    function testSetAgentWalletRevertsExpired() public {
        vm.prank(alice);
        registry.register();

        vm.warp(block.timestamp + 2 hours);

        vm.prank(alice);
        vm.expectRevert(SardisIdentityRegistry.ExpiredDeadline.selector);
        registry.setAgentWallet(0, walletAddress, block.timestamp - 1, "");
    }

    function testSetAgentWalletRevertsZeroAddress() public {
        vm.prank(alice);
        registry.register();

        vm.prank(alice);
        vm.expectRevert(SardisIdentityRegistry.ZeroAddress.selector);
        registry.setAgentWallet(0, address(0), block.timestamp + 1 hours, "");
    }

    function testSetAgentWalletRevertsInvalidSig() public {
        vm.prank(alice);
        registry.register();

        // Wrong signer (alice's key, not walletAddress's key)
        bytes32 structHash = keccak256(
            abi.encode(
                keccak256("SetAgentWallet(uint256 agentId,address newWallet,uint256 deadline)"),
                0,
                walletAddress,
                block.timestamp + 1 hours
            )
        );
        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", registry.DOMAIN_SEPARATOR(), structHash)
        );
        // Sign with a DIFFERENT key (not walletAddress)
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(0xDEAD, digest);
        bytes memory wrongSig = abi.encodePacked(r, s, v);

        vm.prank(alice);
        vm.expectRevert(SardisIdentityRegistry.InvalidSignature.selector);
        registry.setAgentWallet(0, walletAddress, block.timestamp + 1 hours, wrongSig);
    }

    function testUnsetAgentWallet() public {
        vm.startPrank(alice);
        registry.register();
        registry.unsetAgentWallet(0);
        vm.stopPrank();

        assertEq(registry.getAgentWallet(0), address(0));
    }

    // ============ Transfer clears wallet ============

    function testTransferClearsWallet() public {
        vm.prank(alice);
        registry.register();

        assertEq(registry.getAgentWallet(0), alice);

        vm.prank(alice);
        registry.transferFrom(alice, bob, 0);

        assertEq(registry.ownerOf(0), bob);
        assertEq(registry.getAgentWallet(0), address(0)); // Cleared
    }

    // ============ Approved operator can manage ============

    function testApprovedCanSetURI() public {
        vm.prank(alice);
        registry.register("uri");

        vm.prank(alice);
        registry.approve(bob, 0);

        vm.prank(bob);
        registry.setAgentURI(0, "bob-uri");
        assertEq(registry.tokenURI(0), "bob-uri");
    }

    function testApproveForAllCanSetMetadata() public {
        vm.prank(alice);
        registry.register();

        vm.prank(alice);
        registry.setApprovalForAll(bob, true);

        vm.prank(bob);
        registry.setMetadata(0, "x", abi.encode("y"));
    }

    // ============ ERC-721 basics ============

    function testNameAndSymbol() public view {
        assertEq(registry.name(), "Sardis Agent Identity");
        assertEq(registry.symbol(), "SAGENT");
    }

    function testAgentDoesNotExist() public {
        vm.expectRevert(SardisIdentityRegistry.AgentDoesNotExist.selector);
        registry.getAgentWallet(999);
    }
}
