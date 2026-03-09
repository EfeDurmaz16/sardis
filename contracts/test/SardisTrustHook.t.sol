// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/hooks/SardisTrustHook.sol";
import "../src/SardisJobRegistry.sol";

contract SardisTrustHookTest is Test {
    SardisJobRegistry internal registry;
    SardisTrustHook internal hook;

    address internal owner = address(this);
    address internal client = address(0xCAFE);
    address internal provider = address(0xDEAD);
    address internal evaluator = address(0xFACE);

    uint256 internal constant MIN_CLIENT_TRUST = 3000; // 30%
    uint256 internal constant MIN_PROVIDER_JOBS = 2;
    uint256 internal constant MIN_EVALUATOR_TRUST = 3000; // 30%

    function setUp() public {
        registry = new SardisJobRegistry(owner);
        hook = new SardisTrustHook(
            address(registry),
            owner,              // hook owner
            MIN_CLIENT_TRUST,
            MIN_PROVIDER_JOBS,
            MIN_EVALUATOR_TRUST
        );

        // Authorize test contract to write reputation
        registry.setAuthorizedWriter(owner, true);
    }

    // ============ beforeFund: gates on client trust score ============

    function testBeforeFundDeniesLowTrust() public view {
        // Client has no reputation → trust score = 0
        bool result = hook.beforeFund(0, client);
        assertFalse(result);
    }

    function testBeforeFundAllowsHighTrust() public {
        // Give client enough reputation: 5 completed, 0 rejected → 100% = 10000 bp
        _buildReputation(client, 5, 0, 0, 1000);

        bool result = hook.beforeFund(0, client);
        assertTrue(result);
    }

    function testBeforeFundBorderlineTrust() public {
        // Give client exactly 30% trust: 3 completed, 7 rejected = 3000 bp
        _buildReputation(client, 3, 7, 0, 0);

        bool result = hook.beforeFund(0, client);
        assertTrue(result); // 3000 >= 3000
    }

    function testBeforeFundJustBelowThreshold() public {
        // 2 completed, 8 rejected = 2000 bp
        _buildReputation(client, 2, 8, 0, 0);

        bool result = hook.beforeFund(0, client);
        assertFalse(result); // 2000 < 3000
    }

    // ============ beforeSubmit: gates on provider completed jobs ============

    function testBeforeSubmitDeniesNewProvider() public view {
        // Provider has no completed jobs
        bool result = hook.beforeSubmit(0, provider);
        assertFalse(result);
    }

    function testBeforeSubmitAllowsExperiencedProvider() public {
        // Give provider 3 completed jobs
        _buildReputation(provider, 3, 0, 500, 0);

        bool result = hook.beforeSubmit(0, provider);
        assertTrue(result); // 3 >= 2
    }

    function testBeforeSubmitExactMinimum() public {
        // Give provider exactly 2 completed jobs
        _buildReputation(provider, 2, 0, 100, 0);

        bool result = hook.beforeSubmit(0, provider);
        assertTrue(result); // 2 >= 2
    }

    function testBeforeSubmitOneShort() public {
        _buildReputation(provider, 1, 0, 50, 0);

        bool result = hook.beforeSubmit(0, provider);
        assertFalse(result); // 1 < 2
    }

    // ============ beforeEvaluate: gates on evaluator trust score ============

    function testBeforeEvaluateDeniesLowTrust() public view {
        // Evaluator has no reputation
        bool result = hook.beforeEvaluate(0, evaluator, true);
        assertFalse(result);
    }

    function testBeforeEvaluateAllowsHighTrust() public {
        // Give evaluator high reputation
        _buildReputation(evaluator, 10, 1, 0, 0);

        bool result = hook.beforeEvaluate(0, evaluator, true);
        assertTrue(result);
    }

    function testBeforeEvaluateChecksBothApproveAndReject() public {
        _buildReputation(evaluator, 10, 0, 0, 0);

        // Works for both approved=true and approved=false
        assertTrue(hook.beforeEvaluate(0, evaluator, true));
        assertTrue(hook.beforeEvaluate(0, evaluator, false));
    }

    // ============ afterXxx: no-ops ============

    function testAfterFundIsNoOp() public {
        hook.afterFund(0, client);
        // Should not revert
    }

    function testAfterSubmitIsNoOp() public {
        hook.afterSubmit(0, provider);
    }

    function testAfterEvaluateIsNoOp() public {
        hook.afterEvaluate(0, evaluator, true);
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

    function _buildReputation(
        address agent,
        uint256 completed,
        uint256 rejected,
        uint256 earned,
        uint256 spent
    ) internal {
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
