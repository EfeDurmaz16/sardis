// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "./SardisEscrow.sol";

contract GovernanceExecutorFuzzMock {}

/**
 * @title SardisEscrow governance fuzz tests
 * @notice Property tests for arbiter timelock governance controls.
 */
contract SardisEscrowGovernanceFuzzTest is Test {
    SardisEscrow internal escrow;
    address internal arbiter = address(0xA11CE);
    address internal owner;

    uint256 internal constant FEE_BPS = 100;
    uint256 internal constant MIN_AMOUNT = 10 * 10 ** 6;
    uint256 internal constant MAX_DEADLINE_DAYS = 30;

    function setUp() public {
        escrow = new SardisEscrow(arbiter, FEE_BPS, MIN_AMOUNT, MAX_DEADLINE_DAYS);
        owner = escrow.owner();
    }

    function testFuzz_executeArbiterUpdateRequiresTimelock(address newArbiter, uint256 elapsedSeconds) public {
        vm.assume(newArbiter != address(0));
        vm.assume(newArbiter != arbiter);

        escrow.proposeArbiter(newArbiter);

        uint256 timelock = escrow.ARBITER_UPDATE_TIMELOCK();
        elapsedSeconds = bound(elapsedSeconds, 0, timelock - 1);
        vm.warp(block.timestamp + elapsedSeconds);

        vm.expectRevert("Timelock not expired");
        escrow.executeArbiterUpdate();

        assertEq(escrow.arbiter(), arbiter);
        assertEq(escrow.pendingArbiter(), newArbiter);
    }

    function testFuzz_latestProposalWinsAfterTimelock(
        address firstCandidate,
        address secondCandidate,
        uint256 postTimelockDelay
    ) public {
        vm.assume(firstCandidate != address(0));
        vm.assume(secondCandidate != address(0));
        vm.assume(firstCandidate != arbiter);
        vm.assume(secondCandidate != arbiter);
        vm.assume(firstCandidate != secondCandidate);

        escrow.proposeArbiter(firstCandidate);
        uint256 firstEta = escrow.pendingArbiterEta();

        vm.warp(block.timestamp + 1);
        escrow.proposeArbiter(secondCandidate);
        uint256 secondEta = escrow.pendingArbiterEta();

        assertEq(escrow.pendingArbiter(), secondCandidate);
        assertGt(secondEta, firstEta);

        postTimelockDelay = bound(postTimelockDelay, 0, 30 days);
        vm.warp(secondEta + postTimelockDelay);
        escrow.executeArbiterUpdate();

        assertEq(escrow.arbiter(), secondCandidate);
        assertEq(escrow.pendingArbiter(), address(0));
        assertEq(escrow.pendingArbiterEta(), 0);
    }

    function testFuzz_onlyOwnerCanMutateArbiter(address caller, address candidate) public {
        vm.assume(caller != owner);
        vm.assume(candidate != address(0));
        vm.assume(candidate != arbiter);

        vm.prank(caller);
        vm.expectRevert();
        escrow.proposeArbiter(candidate);

        vm.prank(caller);
        vm.expectRevert();
        escrow.cancelArbiterUpdate();

        vm.prank(caller);
        vm.expectRevert();
        escrow.executeArbiterUpdate();
    }

    function testFuzz_governanceExecutorCanMutateArbiter(
        address candidate,
        uint256 delayAfterEta
    ) public {
        vm.assume(candidate != address(0));
        vm.assume(candidate != arbiter);

        GovernanceExecutorFuzzMock governanceExecutor = new GovernanceExecutorFuzzMock();
        address governanceExecutorAddr = address(governanceExecutor);
        vm.assume(governanceExecutorAddr != owner);
        vm.assume(governanceExecutorAddr != arbiter);
        vm.assume(candidate != governanceExecutorAddr);
        escrow.setGovernanceExecutor(governanceExecutorAddr);

        vm.prank(governanceExecutorAddr);
        escrow.proposeArbiter(candidate);

        uint256 eta = escrow.pendingArbiterEta();
        delayAfterEta = bound(delayAfterEta, 0, 30 days);
        vm.warp(eta + delayAfterEta);

        vm.prank(governanceExecutorAddr);
        escrow.executeArbiterUpdate();

        assertEq(escrow.arbiter(), candidate);
    }
}
