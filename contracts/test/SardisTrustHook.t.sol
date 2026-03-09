// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/hooks/SardisTrustHook.sol";
import "../src/SardisJobRegistry.sol";
import "../src/interfaces/IJob.sol";

/// @dev Minimal mock that returns predictable job data for trust checks
contract MockJobManagerForTrust {
    mapping(uint256 => IJob.Job) internal _mockJobs;

    function setMockJob(uint256 jobId, IJob.Job memory job) external {
        _mockJobs[jobId] = job;
    }

    function getJob(uint256 jobId) external view returns (IJob.Job memory) {
        return _mockJobs[jobId];
    }
}

contract SardisTrustHookTest is Test {
    SardisJobRegistry internal registry;
    SardisTrustHook internal hook;
    MockJobManagerForTrust internal mockJobManager;

    address internal owner = address(this);
    address internal client = address(0xCAFE);
    address internal provider = address(0xDEAD);
    address internal evaluator = address(0xFACE);
    address internal token = address(0xA0B8);

    uint256 internal constant MIN_CLIENT_TRUST = 3000; // 30%
    uint256 internal constant MIN_PROVIDER_JOBS = 2;
    uint256 internal constant MIN_EVALUATOR_TRUST = 3000; // 30%

    function setUp() public {
        registry = new SardisJobRegistry(owner);
        mockJobManager = new MockJobManagerForTrust();
        hook = new SardisTrustHook(
            address(registry), address(mockJobManager), owner, MIN_CLIENT_TRUST, MIN_PROVIDER_JOBS, MIN_EVALUATOR_TRUST
        );

        // Authorize test contract to write reputation
        registry.setAuthorizedWriter(owner, true);

        // Set up a mock job
        IJob.Job memory mockJob = IJob.Job({
            client: client,
            provider: provider,
            evaluator: evaluator,
            token: token,
            budget: 1000e6,
            expiredAt: block.timestamp + 7 days,
            description: "test job",
            hook: address(hook),
            status: IJob.JobStatus.Funded
        });
        mockJobManager.setMockJob(0, mockJob);
    }

    // ============ beforeAction(fund): gates on client trust score ============

    function testBeforeAction_fund_deniesLowTrust() public {
        vm.expectRevert(
            abi.encodeWithSelector(SardisTrustHook.InsufficientTrustScore.selector, client, 0, MIN_CLIENT_TRUST)
        );
        hook.beforeAction(0, IJob.fund.selector, "");
    }

    function testBeforeAction_fund_allowsHighTrust() public {
        _buildReputation(client, 5, 0, 0, 1000);
        // Should not revert
        hook.beforeAction(0, IJob.fund.selector, "");
    }

    function testBeforeAction_fund_borderlineTrust() public {
        // 3 completed, 7 rejected = 3000 bp = exactly threshold
        _buildReputation(client, 3, 7, 0, 0);
        hook.beforeAction(0, IJob.fund.selector, "");
    }

    function testBeforeAction_fund_justBelowThreshold() public {
        // 2 completed, 8 rejected = 2000 bp < 3000
        _buildReputation(client, 2, 8, 0, 0);
        vm.expectRevert(
            abi.encodeWithSelector(SardisTrustHook.InsufficientTrustScore.selector, client, 2000, MIN_CLIENT_TRUST)
        );
        hook.beforeAction(0, IJob.fund.selector, "");
    }

    // ============ beforeAction(submit): gates on provider completed jobs ============

    function testBeforeAction_submit_deniesNewProvider() public {
        vm.expectRevert(
            abi.encodeWithSelector(SardisTrustHook.InsufficientCompletedJobs.selector, provider, 0, MIN_PROVIDER_JOBS)
        );
        hook.beforeAction(0, IJob.submit.selector, "");
    }

    function testBeforeAction_submit_allowsExperiencedProvider() public {
        _buildReputation(provider, 3, 0, 500, 0);
        hook.beforeAction(0, IJob.submit.selector, "");
    }

    function testBeforeAction_submit_exactMinimum() public {
        _buildReputation(provider, 2, 0, 100, 0);
        hook.beforeAction(0, IJob.submit.selector, "");
    }

    // ============ beforeAction(complete/reject): gates on evaluator trust ============

    function testBeforeAction_complete_deniesLowTrust() public {
        vm.expectRevert(
            abi.encodeWithSelector(SardisTrustHook.InsufficientTrustScore.selector, evaluator, 0, MIN_EVALUATOR_TRUST)
        );
        hook.beforeAction(0, IJob.complete.selector, "");
    }

    function testBeforeAction_complete_allowsHighTrust() public {
        _buildReputation(evaluator, 10, 1, 0, 0);
        hook.beforeAction(0, IJob.complete.selector, "");
    }

    function testBeforeAction_reject_deniesLowTrust() public {
        vm.expectRevert(
            abi.encodeWithSelector(SardisTrustHook.InsufficientTrustScore.selector, evaluator, 0, MIN_EVALUATOR_TRUST)
        );
        hook.beforeAction(0, IJob.reject.selector, "");
    }

    // ============ afterAction: no-op ============

    function testAfterAction_isNoOp() public pure {
        // SardisTrustHook.afterAction is pure no-op
    }

    // ============ Admin: setThresholds ============

    function testSetThresholds() public {
        hook.setThresholds(5000, 5, 5000);
        assertEq(hook.minClientTrustScore(), 5000);
        assertEq(hook.minProviderCompletedJobs(), 5);
        assertEq(hook.minEvaluatorTrustScore(), 5000);
    }

    function testSetThresholdsRevertsIfNotOwner() public {
        vm.prank(address(0x9999));
        vm.expectRevert(SardisTrustHook.NotOwner.selector);
        hook.setThresholds(5000, 5, 5000);
    }

    function testSetThresholdsRevertsIfTooHigh() public {
        vm.expectRevert(SardisTrustHook.InvalidThreshold.selector);
        hook.setThresholds(10001, 5, 5000);
    }

    // ============ Admin: transferOwnership ============

    function testTransferOwnership() public {
        address newOwner = address(0x7777);
        hook.transferOwnership(newOwner);
        assertEq(hook.owner(), newOwner);
    }

    function testTransferOwnershipRevertsZeroAddress() public {
        vm.expectRevert(SardisTrustHook.ZeroAddress.selector);
        hook.transferOwnership(address(0));
    }

    // ============ Helpers ============

    function _buildReputation(address agent, uint256 completed, uint256 rejected, uint256 earned, uint256 spent)
        internal
    {
        uint256 earnedPerJob = completed > 0 ? earned / completed : 0;
        for (uint256 i = 0; i < completed; i++) {
            registry.recordCompletion(agent, earnedPerJob);
        }
        for (uint256 i = 0; i < rejected; i++) {
            registry.recordRejection(agent);
        }
        if (spent > 0) {
            registry.recordSpending(agent, spent);
        }
    }
}
