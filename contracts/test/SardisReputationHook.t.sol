// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/hooks/SardisReputationHook.sol";
import "../src/SardisJobRegistry.sol";
import "../src/interfaces/IJob.sol";

/// @dev Minimal mock of IJob.getJob() that returns predictable data
contract MockJobManager {
    mapping(uint256 => IJob.Job) internal _mockJobs;

    function setMockJob(uint256 jobId, IJob.Job memory job) external {
        _mockJobs[jobId] = job;
    }

    function getJob(uint256 jobId) external view returns (IJob.Job memory) {
        return _mockJobs[jobId];
    }
}

contract SardisReputationHookTest is Test {
    SardisJobRegistry internal registry;
    SardisReputationHook internal hook;
    MockJobManager internal mockJobManager;

    address internal owner = address(this);
    address internal client = address(0xCAFE);
    address internal provider = address(0xDEAD);
    address internal evaluator = address(0xFACE);
    address internal token = address(0xA0B8);

    function setUp() public {
        registry = new SardisJobRegistry(owner);
        mockJobManager = new MockJobManager();
        hook = new SardisReputationHook(address(registry), address(mockJobManager));

        // Authorize the hook to write to the registry
        registry.setAuthorizedWriter(address(hook), true);

        // Set up a mock job for testing
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

    // ============ beforeAction: always passes ============

    function testBeforeActionNeverReverts() public pure {
        // SardisReputationHook.beforeAction is pure no-op
    }

    // ============ afterAction(fund): tracks client spending ============

    function testAfterAction_fund_recordsSpending() public {
        hook.afterAction(0, IJob.fund.selector, "");

        IJobRegistry.AgentReputation memory rep = registry.getReputation(client);
        assertEq(rep.totalSpent, 1000e6);
        assertGt(rep.lastActiveAt, 0);
    }

    function testAfterAction_fund_accumulatesSpending() public {
        hook.afterAction(0, IJob.fund.selector, "");
        hook.afterAction(0, IJob.fund.selector, "");

        IJobRegistry.AgentReputation memory rep = registry.getReputation(client);
        assertEq(rep.totalSpent, 2000e6);
    }

    // ============ afterAction(complete): records completion ============

    function testAfterAction_complete_recordsCompletion() public {
        hook.afterAction(0, IJob.complete.selector, "");

        IJobRegistry.AgentReputation memory rep = registry.getReputation(provider);
        assertEq(rep.completedJobs, 1);
        assertEq(rep.totalEarned, 1000e6);
        assertGt(rep.lastActiveAt, 0);
    }

    function testAfterAction_complete_multiple() public {
        hook.afterAction(0, IJob.complete.selector, "");
        hook.afterAction(0, IJob.complete.selector, "");

        IJobRegistry.AgentReputation memory rep = registry.getReputation(provider);
        assertEq(rep.completedJobs, 2);
        assertEq(rep.totalEarned, 2000e6);
    }

    // ============ afterAction(reject): records rejection ============

    function testAfterAction_reject_recordsRejection() public {
        // Set job status to Rejected for the mock
        IJob.Job memory rejectedJob = IJob.Job({
            client: client,
            provider: provider,
            evaluator: evaluator,
            token: token,
            budget: 1000e6,
            expiredAt: block.timestamp + 7 days,
            description: "test job",
            hook: address(hook),
            status: IJob.JobStatus.Rejected
        });
        mockJobManager.setMockJob(0, rejectedJob);

        hook.afterAction(0, IJob.reject.selector, "");

        IJobRegistry.AgentReputation memory rep = registry.getReputation(provider);
        assertEq(rep.rejectedJobs, 1);
        assertEq(rep.completedJobs, 0);
    }

    // ============ afterAction(submit): no-op ============

    function testAfterAction_submit_isNoOp() public {
        hook.afterAction(0, IJob.submit.selector, "");
        // No state changes expected
    }

    // ============ Trust score after reputation ============

    function testTrustScoreAfterCompletions() public {
        hook.afterAction(0, IJob.complete.selector, "");
        hook.afterAction(0, IJob.complete.selector, "");
        hook.afterAction(0, IJob.complete.selector, "");

        uint256 score = registry.getTrustScore(provider);
        assertEq(score, 10000);
    }

    function testTrustScoreAfterMixedResults() public {
        hook.afterAction(0, IJob.complete.selector, "");

        // Set rejected status for reject call
        IJob.Job memory rejectedJob = IJob.Job({
            client: client,
            provider: provider,
            evaluator: evaluator,
            token: token,
            budget: 1000e6,
            expiredAt: block.timestamp + 7 days,
            description: "test",
            hook: address(hook),
            status: IJob.JobStatus.Rejected
        });
        mockJobManager.setMockJob(0, rejectedJob);
        hook.afterAction(0, IJob.reject.selector, "");

        uint256 score = registry.getTrustScore(provider);
        assertEq(score, 5000);
    }

    // ============ Constructor validation ============

    function testConstructorRevertsZeroRegistry() public {
        vm.expectRevert(SardisReputationHook.ZeroAddress.selector);
        new SardisReputationHook(address(0), address(mockJobManager));
    }

    function testConstructorRevertsZeroJobManager() public {
        vm.expectRevert(SardisReputationHook.ZeroAddress.selector);
        new SardisReputationHook(address(registry), address(0));
    }
}
