// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SardisJobRegistry.sol";
import "../src/interfaces/IJobRegistry.sol";

contract SardisJobRegistryTest is Test {
    SardisJobRegistry public registry;
    address public owner;
    address public writer;
    address public agent1;
    address public agent2;
    address public unauthorized;

    event CompletionRecorded(address indexed provider, uint256 amount, uint256 completedJobs);
    event RejectionRecorded(address indexed provider, uint256 rejectedJobs);
    event SpendingRecorded(address indexed client, uint256 amount, uint256 totalSpent);
    event AuthorizedWriterSet(address indexed writer, bool authorized);

    function setUp() public {
        owner = address(this);
        writer = address(0xA1);
        agent1 = address(0xB1);
        agent2 = address(0xB2);
        unauthorized = address(0xDEAD);

        registry = new SardisJobRegistry(owner);
        registry.setAuthorizedWriter(writer, true);
    }

    // ── Job registration (completion) ───────────────────────────────

    function testRecordCompletion_updatesReputation() public {
        vm.prank(writer);
        registry.recordCompletion(agent1, 1 ether);

        IJobRegistry.AgentReputation memory rep = registry.getReputation(agent1);
        assertEq(rep.completedJobs, 1);
        assertEq(rep.totalEarned, 1 ether);
        assertGt(rep.lastActiveAt, 0);
    }

    function testRecordCompletion_multipleJobs() public {
        vm.startPrank(writer);
        registry.recordCompletion(agent1, 1 ether);
        registry.recordCompletion(agent1, 2 ether);
        registry.recordCompletion(agent1, 3 ether);
        vm.stopPrank();

        IJobRegistry.AgentReputation memory rep = registry.getReputation(agent1);
        assertEq(rep.completedJobs, 3);
        assertEq(rep.totalEarned, 6 ether);
    }

    function testRecordCompletion_emitsEvent() public {
        vm.prank(writer);

        vm.expectEmit(true, false, false, true);
        emit CompletionRecorded(agent1, 1 ether, 1);

        registry.recordCompletion(agent1, 1 ether);
    }

    // ── Job rejection ───────────────────────────────────────────────

    function testRecordRejection_updatesReputation() public {
        vm.prank(writer);
        registry.recordRejection(agent1);

        IJobRegistry.AgentReputation memory rep = registry.getReputation(agent1);
        assertEq(rep.rejectedJobs, 1);
    }

    function testRecordRejection_emitsEvent() public {
        vm.prank(writer);

        vm.expectEmit(true, false, false, true);
        emit RejectionRecorded(agent1, 1);

        registry.recordRejection(agent1);
    }

    // ── Spending ────────────────────────────────────────────────────

    function testRecordSpending_updatesReputation() public {
        vm.prank(writer);
        registry.recordSpending(agent1, 5 ether);

        IJobRegistry.AgentReputation memory rep = registry.getReputation(agent1);
        assertEq(rep.totalSpent, 5 ether);
    }

    function testRecordSpending_emitsEvent() public {
        vm.prank(writer);

        vm.expectEmit(true, false, false, true);
        emit SpendingRecorded(agent1, 5 ether, 5 ether);

        registry.recordSpending(agent1, 5 ether);
    }

    // ── Trust score ─────────────────────────────────────────────────

    function testGetTrustScore_noJobs_returnsZero() public view {
        uint256 score = registry.getTrustScore(agent1);
        assertEq(score, 0);
    }

    function testGetTrustScore_allCompleted_returns10000() public {
        vm.startPrank(writer);
        registry.recordCompletion(agent1, 0);
        registry.recordCompletion(agent1, 0);
        registry.recordCompletion(agent1, 0);
        vm.stopPrank();

        uint256 score = registry.getTrustScore(agent1);
        assertEq(score, 10000, "100% completion should be 10000 bp");
    }

    function testGetTrustScore_50percentCompletion() public {
        vm.startPrank(writer);
        registry.recordCompletion(agent1, 0);
        registry.recordRejection(agent1);
        vm.stopPrank();

        uint256 score = registry.getTrustScore(agent1);
        assertEq(score, 5000, "50% completion should be 5000 bp");
    }

    function testGetTrustScore_volumeBonus() public {
        vm.startPrank(writer);
        // 10 completions with 1e18 each = 10e18 earned => volumeBonus = 10
        for (uint256 i = 0; i < 10; i++) {
            registry.recordCompletion(agent1, 1 ether);
        }
        vm.stopPrank();

        uint256 score = registry.getTrustScore(agent1);
        // baseScore = 10000, volumeBonus = 10, total = min(10010, 10000) = 10000
        assertEq(score, 10000);
    }

    function testGetTrustScore_volumeBonusCapped() public {
        vm.startPrank(writer);
        // Single large completion
        registry.recordCompletion(agent1, 2000 ether);
        vm.stopPrank();

        uint256 score = registry.getTrustScore(agent1);
        // baseScore = 10000, volumeBonus = min(2000, 1000) = 1000
        // total = min(11000, 10000) = 10000
        assertEq(score, 10000);
    }

    function testGetTrustScore_lowCompletionWithVolume() public {
        vm.startPrank(writer);
        registry.recordCompletion(agent1, 500 ether); // 1 completed, volume bonus
        registry.recordRejection(agent1); // 1 rejected
        vm.stopPrank();

        uint256 score = registry.getTrustScore(agent1);
        // baseScore = (1 * 10000) / 2 = 5000
        // volumeBonus = min(500, 1000) = 500
        // total = 5500
        assertEq(score, 5500);
    }

    // ── Access control ──────────────────────────────────────────────

    function testRecordCompletion_unauthorizedReverts() public {
        vm.prank(unauthorized);
        vm.expectRevert(SardisJobRegistry.NotAuthorizedWriter.selector);
        registry.recordCompletion(agent1, 1 ether);
    }

    function testRecordRejection_unauthorizedReverts() public {
        vm.prank(unauthorized);
        vm.expectRevert(SardisJobRegistry.NotAuthorizedWriter.selector);
        registry.recordRejection(agent1);
    }

    function testRecordSpending_unauthorizedReverts() public {
        vm.prank(unauthorized);
        vm.expectRevert(SardisJobRegistry.NotAuthorizedWriter.selector);
        registry.recordSpending(agent1, 1 ether);
    }

    function testSetAuthorizedWriter_onlyOwner() public {
        vm.prank(unauthorized);
        vm.expectRevert();
        registry.setAuthorizedWriter(writer, false);
    }

    function testSetAuthorizedWriter_zeroAddressReverts() public {
        vm.expectRevert(SardisJobRegistry.ZeroAddress.selector);
        registry.setAuthorizedWriter(address(0), true);
    }

    function testSetAuthorizedWriter_revokeAccess() public {
        registry.setAuthorizedWriter(writer, false);

        vm.prank(writer);
        vm.expectRevert(SardisJobRegistry.NotAuthorizedWriter.selector);
        registry.recordCompletion(agent1, 1 ether);
    }

    function testSetAuthorizedWriter_emitsEvent() public {
        address newWriter = address(0xCAFE);

        vm.expectEmit(true, false, false, true);
        emit AuthorizedWriterSet(newWriter, true);

        registry.setAuthorizedWriter(newWriter, true);
    }

    // ── Multi-agent isolation ───────────────────────────────────────

    function testAgentIsolation() public {
        vm.startPrank(writer);
        registry.recordCompletion(agent1, 1 ether);
        registry.recordRejection(agent2);
        vm.stopPrank();

        IJobRegistry.AgentReputation memory rep1 = registry.getReputation(agent1);
        IJobRegistry.AgentReputation memory rep2 = registry.getReputation(agent2);

        assertEq(rep1.completedJobs, 1);
        assertEq(rep1.rejectedJobs, 0);
        assertEq(rep2.completedJobs, 0);
        assertEq(rep2.rejectedJobs, 1);
    }
}
