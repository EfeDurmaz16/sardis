// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SardisEscrow.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockUSDCEscrowFuzz is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {}
    function decimals() public pure override returns (uint8) { return 6; }
    function mint(address to, uint256 amount) external { _mint(to, amount); }
}

/**
 * @title Fuzz and Invariant Tests for SardisEscrow
 * @notice Ensures escrow accounting invariants hold under random inputs.
 */
contract SardisEscrowFuzzTest is Test {
    SardisEscrow escrow;
    MockUSDCEscrowFuzz usdc;

    address arbiter = address(0x1);
    address buyer = address(0x2);
    address seller = address(0x3);

    uint256 constant FEE_BPS = 100; // 1%
    uint256 constant MIN_AMOUNT = 10 * 10**6;
    uint256 constant MAX_DEADLINE_DAYS = 30;

    function setUp() public {
        escrow = new SardisEscrow(arbiter, FEE_BPS, MIN_AMOUNT, MAX_DEADLINE_DAYS);
        usdc = new MockUSDCEscrowFuzz();
    }

    // ============ Fuzz: Fund and Release Conservation ============

    /// @notice Total funds (seller + fee receiver) after release == funded amount
    function testFuzz_releaseConservesFunds(uint256 amount, uint256 deadlineDays) public {
        amount = bound(amount, MIN_AMOUNT, 100_000 * 10**6);
        deadlineDays = bound(deadlineDays, 1, MAX_DEADLINE_DAYS);
        uint256 deadline = block.timestamp + deadlineDays * 1 days;

        // Create and fund escrow
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller,
            address(usdc),
            amount,
            deadline,
            bytes32(0),
            "fuzz test"
        );

        uint256 fee = (amount * FEE_BPS) / 10000;
        uint256 totalRequired = amount + fee;

        usdc.mint(buyer, totalRequired);
        vm.startPrank(buyer);
        usdc.approve(address(escrow), totalRequired);
        escrow.fundEscrow(escrowId);

        uint256 escrowBalance = usdc.balanceOf(address(escrow));
        assertEq(escrowBalance, totalRequired, "Escrow holds full amount + fee");

        // Seller confirms, buyer approves (auto-releases when both agree)
        vm.stopPrank();
        vm.prank(seller);
        escrow.confirmDelivery(escrowId);
        vm.prank(buyer);
        escrow.approveRelease(escrowId);

        // After release: escrow should have 0 balance
        // seller got amount, owner (deployer) got fee
        uint256 sellerBal = usdc.balanceOf(seller);
        uint256 ownerBal = usdc.balanceOf(address(this)); // deployer = owner
        uint256 escrowBal = usdc.balanceOf(address(escrow));

        assertEq(escrowBal, 0, "Invariant: escrow empty after release");
        assertEq(sellerBal + ownerBal, totalRequired, "Invariant: funds conserved");
        assertEq(sellerBal, amount, "Seller gets amount");
        assertEq(ownerBal, fee, "Owner gets fee");
    }

    // ============ Fuzz: Dispute Resolution Conservation ============

    /// @notice Dispute resolution: buyer + seller amounts + fee == total funded
    function testFuzz_disputeResolutionConservesFunds(uint256 amount, uint256 buyerPercent) public {
        amount = bound(amount, MIN_AMOUNT, 100_000 * 10**6);
        buyerPercent = bound(buyerPercent, 0, 100);

        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller,
            address(usdc),
            amount,
            block.timestamp + 7 days,
            bytes32(0),
            "dispute fuzz"
        );

        uint256 fee = (amount * FEE_BPS) / 10000;
        uint256 totalRequired = amount + fee;

        usdc.mint(buyer, totalRequired);
        vm.startPrank(buyer);
        usdc.approve(address(escrow), totalRequired);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();

        // Raise dispute
        vm.prank(buyer);
        escrow.raiseDispute(escrowId);

        // Arbiter resolves
        vm.prank(arbiter);
        escrow.resolveDispute(escrowId, buyerPercent);

        uint256 buyerBal = usdc.balanceOf(buyer);
        uint256 sellerBal = usdc.balanceOf(seller);
        uint256 ownerBal = usdc.balanceOf(address(this));
        uint256 escrowBal = usdc.balanceOf(address(escrow));

        assertEq(escrowBal, 0, "Invariant: escrow empty after resolution");
        assertEq(
            buyerBal + sellerBal + ownerBal,
            totalRequired,
            "Invariant: funds conserved in dispute resolution"
        );
    }

    // ============ Fuzz: Refund Conservation ============

    /// @notice Expired escrow refund returns all funds to buyer
    function testFuzz_refundReturnsAllFunds(uint256 amount) public {
        amount = bound(amount, MIN_AMOUNT, 100_000 * 10**6);

        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller,
            address(usdc),
            amount,
            block.timestamp + 1 days, // 1 day deadline
            bytes32(0),
            "refund fuzz"
        );

        uint256 fee = (amount * FEE_BPS) / 10000;
        uint256 totalRequired = amount + fee;

        usdc.mint(buyer, totalRequired);
        vm.startPrank(buyer);
        usdc.approve(address(escrow), totalRequired);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();

        // Warp past deadline
        vm.warp(block.timestamp + 2 days);

        uint256 buyerBefore = usdc.balanceOf(buyer);

        vm.prank(buyer);
        escrow.refund(escrowId);

        uint256 buyerAfter = usdc.balanceOf(buyer);
        uint256 escrowBal = usdc.balanceOf(address(escrow));

        assertEq(escrowBal, 0, "Invariant: escrow empty after refund");
        assertEq(buyerAfter - buyerBefore, totalRequired, "Buyer gets full refund including fee");
    }

    // ============ Fuzz: Milestone Amounts ============

    /// @notice Milestone amounts sum must equal escrow amount
    function testFuzz_milestoneAmountsSumToTotal(uint256 amount, uint8 numMilestones) public {
        amount = bound(amount, MIN_AMOUNT, 100_000 * 10**6);
        numMilestones = uint8(bound(numMilestones, 2, 10));

        // Create milestone amounts that sum to total
        uint256[] memory milestoneAmounts = new uint256[](numMilestones);
        uint256 remaining = amount;
        for (uint256 i = 0; i < numMilestones - 1; i++) {
            milestoneAmounts[i] = remaining / (numMilestones - i);
            remaining -= milestoneAmounts[i];
        }
        milestoneAmounts[numMilestones - 1] = remaining;

        // Verify sum
        uint256 sum = 0;
        for (uint256 i = 0; i < numMilestones; i++) {
            sum += milestoneAmounts[i];
        }
        assertEq(sum, amount, "Milestone amounts must sum to total");

        vm.prank(buyer);
        escrow.createEscrowWithMilestones(
            seller,
            address(usdc),
            milestoneAmounts,
            block.timestamp + 7 days,
            bytes32(0),
            "milestone fuzz"
        );
    }
}
