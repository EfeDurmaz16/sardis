// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SardisJobManager.sol";
import "../src/SardisJobRegistry.sol";
import "../src/hooks/SardisTrustHook.sol";
import "../src/hooks/SardisReputationHook.sol";
import "../src/interfaces/IJob.sol";
import "../src/interfaces/IACPHook.sol";

// ============ Mock Contracts ============

contract MockERC20 {
    string public name = "MockUSDC";
    string public symbol = "MUSDC";
    uint8 public decimals = 6;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

contract MockPermissiveHook is IACPHook {
    uint256 public beforeActionCount;
    uint256 public afterActionCount;
    bytes4 public lastSelector;

    function beforeAction(uint256, bytes4 selector, bytes calldata) external override {
        beforeActionCount++;
        lastSelector = selector;
    }

    function afterAction(uint256, bytes4 selector, bytes calldata) external override {
        afterActionCount++;
        lastSelector = selector;
    }
}

contract MockBlockingHook is IACPHook {
    bytes4 public blockSelector;

    constructor(bytes4 _blockSelector) {
        blockSelector = _blockSelector;
    }

    function beforeAction(uint256, bytes4 selector, bytes calldata) external view override {
        if (selector == blockSelector) {
            revert("Hook blocked");
        }
    }

    function afterAction(uint256, bytes4, bytes calldata) external pure override { }
}

contract MockGasGuzzlerHook is IACPHook {
    function beforeAction(uint256, bytes4, bytes calldata) external pure override {
        // Consume all gas — should fail-open
        uint256 i = 0;
        while (true) i++;
    }

    function afterAction(uint256, bytes4, bytes calldata) external pure override { }
}

// ============ Test Contract ============

contract SardisJobManagerTest is Test {
    SardisJobManager public manager;
    MockERC20 public token;

    address public admin = address(0xAD);
    address public feeRecipient = address(0xFE);
    address public client = address(0xC1);
    address public provider = address(0xD1);
    address public evaluator = address(0xE1);

    uint256 public constant FEE_BPS = 100; // 1%
    uint256 public constant JOB_AMOUNT = 1000e6; // 1000 USDC

    function setUp() public {
        manager = new SardisJobManager(admin, feeRecipient, FEE_BPS);
        token = new MockERC20();

        // Allow token
        vm.prank(admin);
        manager.setAllowedToken(address(token), true);

        // Fund client
        token.mint(client, 100_000e6);
    }

    // ============ Helpers ============

    function _createJob() internal returns (uint256) {
        return _createJob(address(0));
    }

    function _createJob(address hook) internal returns (uint256) {
        vm.prank(client);
        return manager.createJob(
            provider, evaluator, block.timestamp + 7 days, "Generate marketing copy for product launch", hook
        );
    }

    function _setBudgetAndFund(uint256 jobId) internal {
        vm.prank(client);
        manager.setBudget(jobId, JOB_AMOUNT, abi.encode(address(token)));

        uint256 fee = (JOB_AMOUNT * FEE_BPS) / 10000;
        vm.startPrank(client);
        token.approve(address(manager), JOB_AMOUNT + fee);
        manager.fund(jobId, JOB_AMOUNT, "");
        vm.stopPrank();
    }

    function _submitJob(uint256 jobId) internal {
        vm.prank(provider);
        manager.submit(jobId, keccak256("deliverable-v1"), "");
    }

    // ============ createJob ============

    function test_createJob() public {
        uint256 jobId = _createJob();
        assertEq(jobId, 0);

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(job.client, client);
        assertEq(job.provider, provider);
        assertEq(job.evaluator, evaluator);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Open));
        assertEq(job.budget, 0); // Not set yet
        assertEq(job.token, address(0)); // Not set yet
    }

    function test_createJob_incrementsCounter() public {
        _createJob();
        _createJob();
        assertEq(manager.jobCounter(), 2);
    }

    function test_createJob_revert_zeroProvider() public {
        vm.prank(client);
        vm.expectRevert(SardisJobManager.ZeroAddress.selector);
        manager.createJob(address(0), evaluator, block.timestamp + 1 days, "test", address(0));
    }

    function test_createJob_revert_sameClientAndProvider() public {
        vm.prank(client);
        vm.expectRevert(SardisJobManager.InvalidParties.selector);
        manager.createJob(client, evaluator, block.timestamp + 1 days, "test", address(0));
    }

    function test_createJob_revert_expiredDeadline() public {
        vm.prank(client);
        vm.expectRevert(SardisJobManager.InvalidExpiry.selector);
        manager.createJob(provider, evaluator, block.timestamp - 1, "test", address(0));
    }

    // ============ setProvider ============

    function test_setProvider() public {
        uint256 jobId = _createJob();
        address newProvider = address(0xD2);

        vm.prank(client);
        manager.setProvider(jobId, newProvider, "");

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(job.provider, newProvider);
    }

    function test_setProvider_revert_notClient() public {
        uint256 jobId = _createJob();
        vm.prank(provider);
        vm.expectRevert(SardisJobManager.NotClient.selector);
        manager.setProvider(jobId, address(0xD2), "");
    }

    // ============ setBudget ============

    function test_setBudget() public {
        uint256 jobId = _createJob();

        vm.prank(client);
        manager.setBudget(jobId, JOB_AMOUNT, abi.encode(address(token)));

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(job.budget, JOB_AMOUNT);
        assertEq(job.token, address(token));
    }

    function test_setBudget_revert_zeroAmount() public {
        uint256 jobId = _createJob();
        vm.prank(client);
        vm.expectRevert(SardisJobManager.InvalidAmount.selector);
        manager.setBudget(jobId, 0, abi.encode(address(token)));
    }

    // ============ fund ============

    function test_fund() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Funded));

        // Check escrow received funds
        uint256 fee = (JOB_AMOUNT * FEE_BPS) / 10000;
        assertEq(manager.jobFees(jobId), fee);
        assertEq(token.balanceOf(address(manager)), JOB_AMOUNT + fee);
    }

    function test_fund_revert_budgetMismatch() public {
        uint256 jobId = _createJob();

        vm.prank(client);
        manager.setBudget(jobId, JOB_AMOUNT, abi.encode(address(token)));

        vm.startPrank(client);
        token.approve(address(manager), JOB_AMOUNT * 2);
        vm.expectRevert(abi.encodeWithSelector(SardisJobManager.BudgetMismatch.selector, JOB_AMOUNT + 1, JOB_AMOUNT));
        manager.fund(jobId, JOB_AMOUNT + 1, "");
        vm.stopPrank();
    }

    function test_fund_revert_budgetNotSet() public {
        uint256 jobId = _createJob();
        vm.prank(client);
        vm.expectRevert(SardisJobManager.BudgetNotSet.selector);
        manager.fund(jobId, 0, "");
    }

    // ============ submit ============

    function test_submit() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);

        bytes32 deliverable = keccak256("result-hash");
        vm.prank(provider);
        manager.submit(jobId, deliverable, "");

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Submitted));
        assertEq(manager.deliverables(jobId), deliverable);
    }

    function test_submit_revert_notProvider() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);

        vm.prank(client);
        vm.expectRevert(SardisJobManager.NotProvider.selector);
        manager.submit(jobId, keccak256("x"), "");
    }

    // ============ complete ============

    function test_complete_releasesToProvider() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);
        _submitJob(jobId);

        uint256 providerBefore = token.balanceOf(provider);
        uint256 feeBefore = token.balanceOf(feeRecipient);

        vm.prank(evaluator);
        manager.complete(jobId, keccak256("good work"), "");

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Completed));
        assertEq(token.balanceOf(provider), providerBefore + JOB_AMOUNT);

        uint256 expectedFee = (JOB_AMOUNT * FEE_BPS) / 10000;
        assertEq(token.balanceOf(feeRecipient), feeBefore + expectedFee);
    }

    function test_complete_usesFeeSnapshotAfterFeeIncrease() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);
        _submitJob(jobId);

        vm.prank(admin);
        manager.setFeeBps(500);

        uint256 providerBefore = token.balanceOf(provider);
        uint256 feeRecipientBefore = token.balanceOf(feeRecipient);

        vm.prank(evaluator);
        manager.complete(jobId, keccak256("good work"), "");

        uint256 fundedFee = (JOB_AMOUNT * FEE_BPS) / 10000;
        assertEq(token.balanceOf(provider), providerBefore + JOB_AMOUNT);
        assertEq(token.balanceOf(feeRecipient), feeRecipientBefore + fundedFee);
        assertEq(token.balanceOf(address(manager)), 0);
    }

    function test_complete_revert_notEvaluator() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);
        _submitJob(jobId);

        vm.prank(client);
        vm.expectRevert(SardisJobManager.NotEvaluator.selector);
        manager.complete(jobId, keccak256("x"), "");
    }

    // ============ reject ============

    function test_reject_openJob_byClient() public {
        uint256 jobId = _createJob();

        vm.prank(client);
        manager.reject(jobId, keccak256("changed mind"), "");

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Rejected));
    }

    function test_reject_fundedJob_byEvaluator_refunds() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);

        uint256 clientBefore = token.balanceOf(client);

        vm.prank(evaluator);
        manager.reject(jobId, keccak256("bad spec"), "");

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Rejected));

        uint256 fee = (JOB_AMOUNT * FEE_BPS) / 10000;
        assertEq(token.balanceOf(client), clientBefore + JOB_AMOUNT + fee);
    }

    function test_reject_submittedJob_byEvaluator_refunds() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);
        _submitJob(jobId);

        uint256 clientBefore = token.balanceOf(client);

        vm.prank(evaluator);
        manager.reject(jobId, keccak256("poor quality"), "");

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Rejected));

        uint256 fee = (JOB_AMOUNT * FEE_BPS) / 10000;
        assertEq(token.balanceOf(client), clientBefore + JOB_AMOUNT + fee);
    }

    function test_reject_usesFeeSnapshotAfterFeeDecrease() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);

        vm.prank(admin);
        manager.setFeeBps(0);

        uint256 clientBefore = token.balanceOf(client);

        vm.prank(evaluator);
        manager.reject(jobId, keccak256("bad spec"), "");

        uint256 fundedFee = (JOB_AMOUNT * FEE_BPS) / 10000;
        assertEq(token.balanceOf(client), clientBefore + JOB_AMOUNT + fundedFee);
        assertEq(token.balanceOf(address(manager)), 0);
    }

    function test_reject_revert_openJob_byNonClient() public {
        uint256 jobId = _createJob();
        vm.prank(evaluator);
        vm.expectRevert(SardisJobManager.NotClient.selector);
        manager.reject(jobId, keccak256("x"), "");
    }

    function test_reject_revert_fundedJob_byNonEvaluator() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);
        vm.prank(client);
        vm.expectRevert(SardisJobManager.NotEvaluator.selector);
        manager.reject(jobId, keccak256("x"), "");
    }

    // ============ claimRefund (expiry) ============

    function test_claimRefund_afterExpiry() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);

        // Advance time past deadline
        vm.warp(block.timestamp + 8 days);

        uint256 clientBefore = token.balanceOf(client);

        manager.claimRefund(jobId);

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Expired));

        uint256 fee = (JOB_AMOUNT * FEE_BPS) / 10000;
        assertEq(token.balanceOf(client), clientBefore + JOB_AMOUNT + fee);
    }

    function test_claimRefund_revert_beforeExpiry() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);

        vm.expectRevert(SardisJobManager.DeadlineNotReached.selector);
        manager.claimRefund(jobId);
    }

    function test_claimRefund_submitted_afterExpiry() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);
        _submitJob(jobId);

        vm.warp(block.timestamp + 8 days);
        manager.claimRefund(jobId);

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Expired));
    }

    function test_claimRefund_usesFeeSnapshotAfterFeeIncrease() public {
        uint256 jobId = _createJob();
        _setBudgetAndFund(jobId);

        vm.prank(admin);
        manager.setFeeBps(500);

        vm.warp(block.timestamp + 8 days);

        uint256 clientBefore = token.balanceOf(client);

        manager.claimRefund(jobId);

        uint256 fundedFee = (JOB_AMOUNT * FEE_BPS) / 10000;
        assertEq(token.balanceOf(client), clientBefore + JOB_AMOUNT + fundedFee);
        assertEq(token.balanceOf(address(manager)), 0);
    }

    // ============ Full lifecycle ============

    function test_fullLifecycle_happyPath() public {
        // 1. Create
        uint256 jobId = _createJob();

        // 2. Set budget
        vm.prank(client);
        manager.setBudget(jobId, JOB_AMOUNT, abi.encode(address(token)));

        // 3. Fund
        uint256 fee = (JOB_AMOUNT * FEE_BPS) / 10000;
        vm.startPrank(client);
        token.approve(address(manager), JOB_AMOUNT + fee);
        manager.fund(jobId, JOB_AMOUNT, "");
        vm.stopPrank();

        // 4. Submit
        vm.prank(provider);
        manager.submit(jobId, keccak256("deliverable"), "");

        // 5. Complete
        uint256 providerBefore = token.balanceOf(provider);
        vm.prank(evaluator);
        manager.complete(jobId, keccak256("approved"), "");

        assertEq(token.balanceOf(provider), providerBefore + JOB_AMOUNT);
    }

    // ============ Hooks (IACPHook) ============

    function test_hook_permissive_tracksCallbacks() public {
        MockPermissiveHook hook = new MockPermissiveHook();
        uint256 jobId = _createJob(address(hook));

        vm.prank(client);
        manager.setBudget(jobId, JOB_AMOUNT, abi.encode(address(token)));

        uint256 fee = (JOB_AMOUNT * FEE_BPS) / 10000;
        vm.startPrank(client);
        token.approve(address(manager), JOB_AMOUNT + fee);
        manager.fund(jobId, JOB_AMOUNT, "");
        vm.stopPrank();

        // fund triggers before + after = 2 calls (setBudget also triggers 2)
        assertGt(hook.beforeActionCount(), 0);
        assertGt(hook.afterActionCount(), 0);
    }

    function test_hook_blocking_preventsFund() public {
        MockBlockingHook hook = new MockBlockingHook(IJob.fund.selector);
        uint256 jobId = _createJob(address(hook));

        vm.prank(client);
        manager.setBudget(jobId, JOB_AMOUNT, abi.encode(address(token)));

        uint256 fee = (JOB_AMOUNT * FEE_BPS) / 10000;
        vm.startPrank(client);
        token.approve(address(manager), JOB_AMOUNT + fee);

        // Hook explicitly reverts → propagates, blocking the fund
        vm.expectRevert("Hook blocked");
        manager.fund(jobId, JOB_AMOUNT, "");
        vm.stopPrank();
    }

    function test_hook_blocking_preventsSubmit() public {
        MockBlockingHook hook = new MockBlockingHook(IJob.submit.selector);
        uint256 jobId = _createJob(address(hook));
        _setBudgetAndFund(jobId);

        vm.prank(provider);
        // Hook explicitly reverts → propagates, blocking the submit
        vm.expectRevert("Hook blocked");
        manager.submit(jobId, keccak256("x"), "");
    }

    function test_hook_gasGuzzler_failsOpen() public {
        MockGasGuzzlerHook hook = new MockGasGuzzlerHook();
        uint256 jobId = _createJob(address(hook));

        vm.prank(client);
        manager.setBudget(jobId, JOB_AMOUNT, abi.encode(address(token)));

        uint256 fee = (JOB_AMOUNT * FEE_BPS) / 10000;
        vm.startPrank(client);
        token.approve(address(manager), JOB_AMOUNT + fee);

        // Gas guzzler hook exhausts gas (no return data) → fail-open, fund succeeds
        manager.fund(jobId, JOB_AMOUNT, "");
        vm.stopPrank();

        IJob.Job memory job = manager.getJob(jobId);
        assertEq(uint256(job.status), uint256(IJob.JobStatus.Funded));
    }

    // ============ Admin ============

    function test_admin_setFeeBps() public {
        vm.prank(admin);
        manager.setFeeBps(200);
        assertEq(manager.feeBps(), 200);
    }

    function test_admin_setFeeBps_revert_tooHigh() public {
        vm.prank(admin);
        vm.expectRevert(SardisJobManager.FeeTooHigh.selector);
        manager.setFeeBps(501);
    }

    function test_admin_pause() public {
        vm.prank(admin);
        manager.pause();

        vm.prank(client);
        vm.expectRevert();
        manager.createJob(provider, evaluator, block.timestamp + 1 days, "test", address(0));
    }

    // ============ getJobs batch ============

    function test_getJobs_batch() public {
        uint256 id0 = _createJob();
        uint256 id1 = _createJob();

        uint256[] memory ids = new uint256[](2);
        ids[0] = id0;
        ids[1] = id1;

        IJob.Job[] memory jobs = manager.getJobs(ids);
        assertEq(jobs.length, 2);
        assertEq(jobs[0].client, client);
        assertEq(jobs[1].client, client);
    }
}
