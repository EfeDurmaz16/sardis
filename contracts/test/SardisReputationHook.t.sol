// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/hooks/SardisReputationHook.sol";
import "../src/SardisJobRegistry.sol";
import "../src/interfaces/IJob.sol";

/// @dev Minimal mock of IJob.getJob() that returns predictable data
contract MockJobManager is IJob {
    mapping(uint256 => Job) internal _mockJobs;

    function setMockJob(uint256 jobId, Job memory job) external {
        _mockJobs[jobId] = job;
    }

    function getJob(uint256 jobId) external view override returns (Job memory) {
        return _mockJobs[jobId];
    }

    // Unused lifecycle functions — revert
    function createJob(address, address, address, uint256, uint256, bytes32, address) external pure override returns (uint256) { revert("not implemented"); }
    function fundJob(uint256) external pure override { revert("not implemented"); }
    function submitJob(uint256, bytes32) external pure override { revert("not implemented"); }
    function evaluateJob(uint256, bool) external pure override { revert("not implemented"); }
    function expireJob(uint256) external pure override { revert("not implemented"); }
    function cancelJob(uint256) external pure override { revert("not implemented"); }
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
            amount: 1000e6,
            deadline: block.timestamp + 7 days,
            jobHash: keccak256("test-job"),
            hook: address(hook),
            status: IJob.JobStatus.Funded
        });
        mockJobManager.setMockJob(0, mockJob);
    }

    // ============ beforeFund: always returns true ============

    function testBeforeFundAlwaysReturnsTrue() public pure {
        // SardisReputationHook.beforeFund is pure and always returns true
        // We just verify the interface is correct
    }

    function testBeforeFundReturnsTrueForAnyAddress() public view {
        bool result = hook.beforeFund(0, client);
        assertTrue(result);

        result = hook.beforeFund(0, address(0));
        assertTrue(result);
    }

    // ============ beforeSubmit: always returns true ============

    function testBeforeSubmitAlwaysReturnsTrue() public view {
        bool result = hook.beforeSubmit(0, provider);
        assertTrue(result);
    }

    // ============ beforeEvaluate: always returns true ============

    function testBeforeEvaluateAlwaysReturnsTrue() public view {
        bool result = hook.beforeEvaluate(0, evaluator, true);
        assertTrue(result);

        result = hook.beforeEvaluate(0, evaluator, false);
        assertTrue(result);
    }

    // ============ afterFund: tracks client spending ============

    function testAfterFundRecordsSpending() public {
        hook.afterFund(0, client);

        IJobRegistry.AgentReputation memory rep = registry.getReputation(client);
        assertEq(rep.totalSpent, 1000e6);
        assertGt(rep.lastActiveAt, 0);
    }

    function testAfterFundAccumulatesSpending() public {
        hook.afterFund(0, client);
        hook.afterFund(0, client);

        IJobRegistry.AgentReputation memory rep = registry.getReputation(client);
        assertEq(rep.totalSpent, 2000e6);
    }

    // ============ afterEvaluate(approved): records completion ============

    function testAfterEvaluateApprovedRecordsCompletion() public {
        hook.afterEvaluate(0, evaluator, true);

        IJobRegistry.AgentReputation memory rep = registry.getReputation(provider);
        assertEq(rep.completedJobs, 1);
        assertEq(rep.totalEarned, 1000e6);
        assertGt(rep.lastActiveAt, 0);
    }

    function testAfterEvaluateApprovedMultiple() public {
        hook.afterEvaluate(0, evaluator, true);
        hook.afterEvaluate(0, evaluator, true);

        IJobRegistry.AgentReputation memory rep = registry.getReputation(provider);
        assertEq(rep.completedJobs, 2);
        assertEq(rep.totalEarned, 2000e6);
    }

    // ============ afterEvaluate(rejected): records rejection ============

    function testAfterEvaluateRejectedRecordsRejection() public {
        hook.afterEvaluate(0, evaluator, false);

        IJobRegistry.AgentReputation memory rep = registry.getReputation(provider);
        assertEq(rep.rejectedJobs, 1);
        assertEq(rep.completedJobs, 0);
    }

    // ============ afterSubmit: no-op ============

    function testAfterSubmitIsNoOp() public {
        hook.afterSubmit(0, provider);
        // No state changes expected
    }

    // ============ Trust score after reputation ============

    function testTrustScoreAfterCompletions() public {
        // 3 completions, 0 rejections → 100% = 10000 bp
        hook.afterEvaluate(0, evaluator, true);
        hook.afterEvaluate(0, evaluator, true);
        hook.afterEvaluate(0, evaluator, true);

        uint256 score = registry.getTrustScore(provider);
        assertEq(score, 10000); // 100% success rate (no volume bonus since amount < 1e18)
    }

    function testTrustScoreAfterMixedResults() public {
        // 1 completion, 1 rejection → 50% = 5000 bp
        hook.afterEvaluate(0, evaluator, true);
        hook.afterEvaluate(0, evaluator, false);

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
