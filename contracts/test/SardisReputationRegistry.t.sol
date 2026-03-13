// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SardisReputationRegistry.sol";
import "../src/SardisIdentityRegistry.sol";
import "../src/interfaces/IReputationRegistry.sol";

contract SardisReputationRegistryTest is Test {
    SardisIdentityRegistry internal identity;
    SardisReputationRegistry internal reputation;

    address internal agentOwner = address(0xA11CE);
    address internal client1 = address(0xC1);
    address internal client2 = address(0xC2);
    address internal responder = address(0xDE);

    uint256 internal agentId;

    function setUp() public {
        identity = new SardisIdentityRegistry();
        reputation = new SardisReputationRegistry(address(identity));

        // Register an agent
        vm.prank(agentOwner);
        agentId = identity.register("https://agent.example.com");
    }

    // ============ getIdentityRegistry ============

    function testGetIdentityRegistry() public view {
        assertEq(reputation.getIdentityRegistry(), address(identity));
    }

    // ============ Constructor ============

    function testConstructorRevertsZeroAddress() public {
        vm.expectRevert(SardisReputationRegistry.ZeroAddress.selector);
        new SardisReputationRegistry(address(0));
    }

    // ============ giveFeedback ============

    function testGiveFeedback() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 80, 0, "quality", "speed", "", "", bytes32(0));

        (int128 value, uint8 dec, string memory t1, string memory t2, bool revoked) =
            reputation.readFeedback(agentId, client1, 0);
        assertEq(value, 80);
        assertEq(dec, 0);
        assertEq(t1, "quality");
        assertEq(t2, "speed");
        assertFalse(revoked);
    }

    function testGiveFeedbackNegative() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, -50, 2, "", "", "", "", bytes32(0));

        (int128 value, uint8 dec,,,) = reputation.readFeedback(agentId, client1, 0);
        assertEq(value, -50);
        assertEq(dec, 2);
    }

    function testGiveFeedbackMultiple() public {
        vm.startPrank(client1);
        reputation.giveFeedback(agentId, 90, 0, "", "", "", "", bytes32(0));
        reputation.giveFeedback(agentId, 70, 0, "", "", "", "", bytes32(0));
        vm.stopPrank();

        assertEq(reputation.getLastIndex(agentId, client1), 2);
    }

    function testGiveFeedbackRevertsOwner() public {
        vm.prank(agentOwner);
        vm.expectRevert(SardisReputationRegistry.SelfFeedback.selector);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));
    }

    function testGiveFeedbackRevertsApproved() public {
        vm.prank(agentOwner);
        identity.approve(client1, agentId);

        vm.prank(client1);
        vm.expectRevert(SardisReputationRegistry.SelfFeedback.selector);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));
    }

    function testGiveFeedbackRevertsApprovedForAll() public {
        vm.prank(agentOwner);
        identity.setApprovalForAll(client1, true);

        vm.prank(client1);
        vm.expectRevert(SardisReputationRegistry.SelfFeedback.selector);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));
    }

    function testGiveFeedbackRevertsInvalidDecimals() public {
        vm.prank(client1);
        vm.expectRevert(SardisReputationRegistry.InvalidDecimals.selector);
        reputation.giveFeedback(agentId, 100, 19, "", "", "", "", bytes32(0));
    }

    function testGiveFeedbackRevertsNonexistentAgent() public {
        vm.prank(client1);
        vm.expectRevert(SardisReputationRegistry.AgentDoesNotExist.selector);
        reputation.giveFeedback(999, 100, 0, "", "", "", "", bytes32(0));
    }

    function testGiveFeedbackEmitsEvent() public {
        vm.prank(client1);
        vm.expectEmit(true, true, false, false);
        emit IReputationRegistry.NewFeedback(
            agentId, client1, 0, 80, 0, "quality", "quality", "speed", "", "", bytes32(0)
        );
        reputation.giveFeedback(agentId, 80, 0, "quality", "speed", "", "", bytes32(0));
    }

    // ============ revokeFeedback ============

    function testRevokeFeedback() public {
        vm.startPrank(client1);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));
        reputation.revokeFeedback(agentId, 0);
        vm.stopPrank();

        (,,,, bool revoked) = reputation.readFeedback(agentId, client1, 0);
        assertTrue(revoked);
    }

    function testRevokeFeedbackRevertsNotSubmitter() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));

        // client2 tries to revoke client1's feedback
        vm.prank(client2);
        vm.expectRevert(SardisReputationRegistry.FeedbackDoesNotExist.selector);
        reputation.revokeFeedback(agentId, 0);
    }

    function testRevokeFeedbackRevertsAlreadyRevoked() public {
        vm.startPrank(client1);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));
        reputation.revokeFeedback(agentId, 0);

        vm.expectRevert(SardisReputationRegistry.AlreadyRevoked.selector);
        reputation.revokeFeedback(agentId, 0);
        vm.stopPrank();
    }

    function testRevokeFeedbackEmitsEvent() public {
        vm.startPrank(client1);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));

        vm.expectEmit(true, true, true, false);
        emit IReputationRegistry.FeedbackRevoked(agentId, client1, 0);
        reputation.revokeFeedback(agentId, 0);
        vm.stopPrank();
    }

    // ============ appendResponse ============

    function testAppendResponse() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 50, 0, "", "", "", "", bytes32(0));

        // Only agent owner or approved can respond
        vm.prank(agentOwner);
        reputation.appendResponse(agentId, client1, 0, "https://response.com", keccak256("resp"));

        address[] memory resp = new address[](1);
        resp[0] = agentOwner;
        uint64 count = reputation.getResponseCount(agentId, client1, 0, resp);
        assertEq(count, 1);
    }

    function testAppendResponseRevertsNonexistent() public {
        // Agent owner trying to respond to nonexistent feedback
        vm.prank(agentOwner);
        vm.expectRevert(SardisReputationRegistry.FeedbackDoesNotExist.selector);
        reputation.appendResponse(agentId, client1, 0, "", bytes32(0));
    }

    function testAppendResponseRevertsNotOwner() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 50, 0, "", "", "", "", bytes32(0));

        vm.prank(responder);
        vm.expectRevert(SardisReputationRegistry.NotAgentOwnerOrApproved.selector);
        reputation.appendResponse(agentId, client1, 0, "", bytes32(0));
    }

    function testAppendResponseEmitsEvent() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 50, 0, "", "", "", "", bytes32(0));

        vm.prank(agentOwner);
        vm.expectEmit(true, true, false, true);
        emit IReputationRegistry.ResponseAppended(agentId, client1, 0, agentOwner, "https://resp.com", keccak256("r"));
        reputation.appendResponse(agentId, client1, 0, "https://resp.com", keccak256("r"));
    }

    // ============ getSummary ============

    function testGetSummaryBasic() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 80, 0, "", "", "", "", bytes32(0));
        vm.prank(client2);
        reputation.giveFeedback(agentId, 60, 0, "", "", "", "", bytes32(0));

        address[] memory clients = new address[](2);
        clients[0] = client1;
        clients[1] = client2;

        (uint64 count, int128 avg, uint8 dec) = reputation.getSummary(agentId, clients, "", "");
        assertEq(count, 2);
        assertEq(avg, 70); // (80+60)/2
        assertEq(dec, 0);
    }

    function testGetSummaryExcludesRevoked() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));
        vm.prank(client1);
        reputation.revokeFeedback(agentId, 0);

        vm.prank(client2);
        reputation.giveFeedback(agentId, 60, 0, "", "", "", "", bytes32(0));

        address[] memory clients = new address[](2);
        clients[0] = client1;
        clients[1] = client2;

        (uint64 count, int128 avg,) = reputation.getSummary(agentId, clients, "", "");
        assertEq(count, 1);
        assertEq(avg, 60);
    }

    function testGetSummaryWithTagFilter() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 90, 0, "quality", "", "", "", bytes32(0));
        vm.prank(client1);
        reputation.giveFeedback(agentId, 50, 0, "speed", "", "", "", bytes32(0));

        address[] memory clients = new address[](1);
        clients[0] = client1;

        (uint64 count, int128 avg,) = reputation.getSummary(agentId, clients, "quality", "");
        assertEq(count, 1);
        assertEq(avg, 90);
    }

    // ============ readAllFeedback ============

    function testReadAllFeedback() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 80, 0, "t1", "t2", "", "", bytes32(0));
        vm.prank(client2);
        reputation.giveFeedback(agentId, 60, 0, "t1", "t2", "", "", bytes32(0));

        address[] memory clients = new address[](2);
        clients[0] = client1;
        clients[1] = client2;

        (
            address[] memory retClients,
            uint64[] memory indexes,
            int128[] memory values,
            uint8[] memory decs,
            string[] memory t1s,
            string[] memory t2s,
            bool[] memory revoked
        ) = reputation.readAllFeedback(agentId, clients, "", "", false);

        assertEq(retClients.length, 2);
        assertEq(values[0], 80);
        assertEq(values[1], 60);
        assertEq(indexes[0], 0);
        assertEq(indexes[1], 0);
        assertFalse(revoked[0]);
        assertFalse(revoked[1]);
    }

    function testReadAllFeedbackExcludesRevoked() public {
        vm.startPrank(client1);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));
        reputation.revokeFeedback(agentId, 0);
        reputation.giveFeedback(agentId, 80, 0, "", "", "", "", bytes32(0));
        vm.stopPrank();

        address[] memory clients = new address[](1);
        clients[0] = client1;

        (address[] memory retClients,, int128[] memory values,,,, bool[] memory revoked) =
            reputation.readAllFeedback(agentId, clients, "", "", false);

        assertEq(retClients.length, 1);
        assertEq(values[0], 80);
        assertFalse(revoked[0]);
    }

    function testReadAllFeedbackIncludesRevoked() public {
        vm.startPrank(client1);
        reputation.giveFeedback(agentId, 100, 0, "", "", "", "", bytes32(0));
        reputation.revokeFeedback(agentId, 0);
        vm.stopPrank();

        address[] memory clients = new address[](1);
        clients[0] = client1;

        (,,,,,, bool[] memory revoked) = reputation.readAllFeedback(agentId, clients, "", "", true);
        assertEq(revoked.length, 1);
        assertTrue(revoked[0]);
    }

    // ============ getClients ============

    function testGetClients() public {
        vm.prank(client1);
        reputation.giveFeedback(agentId, 80, 0, "", "", "", "", bytes32(0));
        vm.prank(client2);
        reputation.giveFeedback(agentId, 60, 0, "", "", "", "", bytes32(0));

        address[] memory clients = reputation.getClients(agentId);
        assertEq(clients.length, 2);
        assertEq(clients[0], client1);
        assertEq(clients[1], client2);
    }

    function testGetClientsNoDuplicates() public {
        vm.startPrank(client1);
        reputation.giveFeedback(agentId, 80, 0, "", "", "", "", bytes32(0));
        reputation.giveFeedback(agentId, 90, 0, "", "", "", "", bytes32(0));
        vm.stopPrank();

        address[] memory clients = reputation.getClients(agentId);
        assertEq(clients.length, 1);
    }

    // ============ getLastIndex ============

    function testGetLastIndex() public {
        assertEq(reputation.getLastIndex(agentId, client1), 0);

        vm.startPrank(client1);
        reputation.giveFeedback(agentId, 80, 0, "", "", "", "", bytes32(0));
        assertEq(reputation.getLastIndex(agentId, client1), 1);

        reputation.giveFeedback(agentId, 90, 0, "", "", "", "", bytes32(0));
        assertEq(reputation.getLastIndex(agentId, client1), 2);
        vm.stopPrank();
    }

    // ============ readFeedback errors ============

    function testReadFeedbackRevertsNonexistent() public {
        vm.expectRevert(SardisReputationRegistry.FeedbackDoesNotExist.selector);
        reputation.readFeedback(agentId, client1, 0);
    }
}
