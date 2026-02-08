// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SardisWalletFactory.sol";
import "../src/SardisAgentWallet.sol";
import "../src/SardisEscrow.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {
        _mint(msg.sender, 10_000_000 * 10**6); // 10M USDC
    }

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

/**
 * @title End-to-End Test Suite
 * @notice Tests complete user flows across all Sardis contracts
 */
contract E2ETest is Test {
    // Contracts
    SardisWalletFactory factory;
    SardisEscrow escrow;
    MockUSDC usdc;

    // Actors
    address deployer;
    address agent1 = address(0x1001);
    address agent2 = address(0x1002);
    address merchant = address(0x2001);
    address recovery = address(0x3001);
    address arbiter = address(0x4001);

    // Config
    uint256 constant LIMIT_PER_TX = 1000 * 10**6;   // 1000 USDC
    uint256 constant DAILY_LIMIT = 5000 * 10**6;    // 5000 USDC
    uint256 constant FEE_BPS = 100;                  // 1%
    uint256 constant MIN_ESCROW = 10 * 10**6;        // 10 USDC

    function setUp() public {
        deployer = address(this);

        // Deploy mock USDC
        usdc = new MockUSDC();

        // Deploy factory
        factory = new SardisWalletFactory(
            LIMIT_PER_TX,
            DAILY_LIMIT,
            recovery
        );

        // Deploy escrow
        escrow = new SardisEscrow(
            arbiter,
            FEE_BPS,
            MIN_ESCROW,
            30 // max deadline days
        );

        // Fund agents with USDC for testing
        usdc.transfer(agent1, 100_000 * 10**6);
        usdc.transfer(agent2, 100_000 * 10**6);
    }

    // ============================================================
    // E2E Test 1: Complete Wallet Lifecycle
    // ============================================================
    function test_E2E_WalletLifecycle() public {
        console.log("\n=== E2E Test: Wallet Lifecycle ===\n");

        // Step 1: Create wallet for agent1
        console.log("Step 1: Creating wallet for agent1...");
        address walletAddr = factory.createWallet(agent1);
        SardisAgentWallet wallet = SardisAgentWallet(payable(walletAddr));

        assertTrue(factory.isValidWallet(walletAddr), "Wallet should be valid");
        assertEq(wallet.agent(), agent1, "Agent should be set");
        assertEq(wallet.sardis(), address(factory), "Factory should be Sardis");
        console.log("  Wallet created at:", walletAddr);

        // Step 2: Fund wallet with USDC
        console.log("Step 2: Funding wallet with 10,000 USDC...");
        usdc.transfer(walletAddr, 10_000 * 10**6);
        assertEq(wallet.getBalance(address(usdc)), 10_000 * 10**6);
        console.log("  Balance:", wallet.getBalance(address(usdc)) / 10**6, "USDC");

        // Step 3: Agent makes a payment
        console.log("Step 3: Agent making 500 USDC payment to merchant...");
        vm.prank(agent1);
        bytes32 txHash = wallet.pay(address(usdc), merchant, 500 * 10**6, "Coffee supplies");

        assertTrue(txHash != bytes32(0), "Should return tx hash");
        assertEq(usdc.balanceOf(merchant), 500 * 10**6, "Merchant should receive payment");
        assertEq(wallet.spentToday(), 500 * 10**6, "Spent today should update");
        console.log("  Payment successful, merchant balance:", usdc.balanceOf(merchant) / 10**6, "USDC");

        // Step 4: Test spending limits
        console.log("Step 4: Testing per-tx limit (should fail for 1001 USDC)...");
        vm.prank(agent1);
        vm.expectRevert("Exceeds per-tx limit");
        wallet.pay(address(usdc), merchant, 1001 * 10**6, "Too large");
        console.log("  Correctly rejected payment exceeding per-tx limit");

        // Step 5: Test daily limit
        console.log("Step 5: Testing daily limit...");
        // Already spent 500, daily limit is 5000, so we can spend 4500 more
        for (uint i = 0; i < 4; i++) {
            vm.prank(agent1);
            wallet.pay(address(usdc), merchant, 1000 * 10**6, "Batch payment");
        }
        // Now spent 4500, try to spend 600 more (should fail, would be 5100 > 5000)
        vm.prank(agent1);
        vm.expectRevert("Exceeds daily limit");
        wallet.pay(address(usdc), merchant, 600 * 10**6, "Over daily limit");
        console.log("  Correctly rejected payment exceeding daily limit");
        console.log("  Total spent today:", wallet.spentToday() / 10**6, "USDC");

        // Step 6: Test daily reset
        console.log("Step 6: Testing daily limit reset...");
        vm.warp(block.timestamp + 1 days);
        vm.prank(agent1);
        wallet.pay(address(usdc), merchant, 500 * 10**6, "Next day payment");
        assertEq(wallet.spentToday(), 500 * 10**6, "Spent should reset to new payment");
        console.log("  Daily limit reset working, spent today:", wallet.spentToday() / 10**6, "USDC");

        console.log("\n=== Wallet Lifecycle Test PASSED ===\n");
    }

    // ============================================================
    // E2E Test 2: Hold (Pre-Authorization) Flow
    // ============================================================
    function test_E2E_HoldFlow() public {
        console.log("\n=== E2E Test: Hold Flow ===\n");

        // Setup: Create and fund wallet
        address walletAddr = factory.createWallet(agent1);
        SardisAgentWallet wallet = SardisAgentWallet(payable(walletAddr));
        usdc.transfer(walletAddr, 5000 * 10**6);

        // Step 1: Create a hold
        console.log("Step 1: Creating 200 USDC hold for merchant...");
        vm.prank(agent1);
        bytes32 holdId = wallet.createHold(merchant, address(usdc), 200 * 10**6, 1 hours);

        assertTrue(holdId != bytes32(0), "Should return hold ID");
        assertEq(wallet.totalHeldAmount(address(usdc)), 200 * 10**6, "Held amount should update");
        console.log("  Hold created, total held:", wallet.totalHeldAmount(address(usdc)) / 10**6, "USDC");

        // Step 2: Verify available balance
        console.log("Step 2: Checking available balance...");
        uint256 available = wallet.getAvailableBalance(address(usdc));
        assertEq(available, 4800 * 10**6, "Available should be 4800 USDC");
        console.log("  Total balance: 5000 USDC, Available:", available / 10**6, "USDC");

        // Step 3: Create another hold (test over-commitment prevention)
        console.log("Step 3: Testing over-commitment prevention...");
        vm.prank(agent1);
        vm.expectRevert("Insufficient available balance");
        wallet.createHold(merchant, address(usdc), 5000 * 10**6, 1 hours);
        console.log("  Correctly rejected hold exceeding available balance");

        // Step 4: Capture partial amount
        console.log("Step 4: Capturing 150 USDC of 200 USDC hold...");
        uint256 merchantBefore = usdc.balanceOf(merchant);
        vm.prank(agent1);
        wallet.captureHold(holdId, 150 * 10**6);

        assertEq(usdc.balanceOf(merchant), merchantBefore + 150 * 10**6, "Merchant should receive 150");
        assertEq(wallet.totalHeldAmount(address(usdc)), 0, "Held amount should be released");
        console.log("  Captured 150 USDC, merchant received payment");

        // Step 5: Create and void a hold
        console.log("Step 5: Testing hold void...");
        vm.prank(agent1);
        bytes32 holdId2 = wallet.createHold(merchant, address(usdc), 300 * 10**6, 1 hours);
        assertEq(wallet.totalHeldAmount(address(usdc)), 300 * 10**6);

        vm.prank(agent1);
        wallet.voidHold(holdId2);
        assertEq(wallet.totalHeldAmount(address(usdc)), 0, "Void should release held amount");
        console.log("  Hold voided, funds released");

        console.log("\n=== Hold Flow Test PASSED ===\n");
    }

    // ============================================================
    // E2E Test 3: Merchant Allowlist/Denylist
    // ============================================================
    function test_E2E_MerchantRestrictions() public {
        console.log("\n=== E2E Test: Merchant Restrictions ===\n");

        // Setup
        address walletAddr = factory.createWallet(agent1);
        SardisAgentWallet wallet = SardisAgentWallet(payable(walletAddr));
        usdc.transfer(walletAddr, 5000 * 10**6);

        address allowedMerchant = address(0x5001);
        address blockedMerchant = address(0x5002);

        // Step 1: Test denylist mode (default)
        console.log("Step 1: Testing denylist mode...");
        vm.prank(address(factory)); // Factory is Sardis
        wallet.denyMerchant(blockedMerchant);

        vm.prank(agent1);
        vm.expectRevert("Merchant denied");
        wallet.pay(address(usdc), blockedMerchant, 100 * 10**6, "Blocked");
        console.log("  Payment to denied merchant correctly rejected");

        // Step 2: Switch to allowlist mode
        console.log("Step 2: Switching to allowlist mode...");
        vm.prank(address(factory));
        wallet.setAllowlistMode(true);

        vm.prank(address(factory));
        wallet.allowMerchant(allowedMerchant);

        // Payment to allowed merchant should work
        vm.prank(agent1);
        wallet.pay(address(usdc), allowedMerchant, 100 * 10**6, "Allowed");
        console.log("  Payment to allowed merchant succeeded");

        // Payment to non-allowed merchant should fail
        vm.prank(agent1);
        vm.expectRevert("Merchant not allowed");
        wallet.pay(address(usdc), merchant, 100 * 10**6, "Not allowed");
        console.log("  Payment to non-allowed merchant correctly rejected");

        console.log("\n=== Merchant Restrictions Test PASSED ===\n");
    }

    // ============================================================
    // E2E Test 4: Escrow Flow (Agent-to-Agent Payment)
    // ============================================================
    function test_E2E_EscrowFlow() public {
        console.log("\n=== E2E Test: Escrow Flow ===\n");

        uint256 escrowAmount = 1000 * 10**6; // 1000 USDC
        uint256 fee = (escrowAmount * FEE_BPS) / 10000; // 10 USDC

        // Step 1: Agent1 (buyer) creates escrow with Agent2 (seller)
        console.log("Step 1: Agent1 creating 1000 USDC escrow with Agent2...");
        vm.prank(agent1);
        uint256 escrowId = escrow.createEscrow(
            agent2,                          // seller
            address(usdc),                   // token
            escrowAmount,                    // amount
            block.timestamp + 7 days,        // deadline
            bytes32(0),                      // no condition
            "AI model training service"      // description
        );

        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertEq(e.buyer, agent1);
        assertEq(e.seller, agent2);
        assertEq(e.amount, escrowAmount);
        assertEq(e.fee, fee);
        console.log("  Escrow created, ID:", escrowId);
        console.log("  Amount: 1000 USDC, Fee: 10 USDC");

        // Step 2: Buyer funds the escrow
        console.log("Step 2: Buyer funding escrow...");
        vm.startPrank(agent1);
        usdc.approve(address(escrow), escrowAmount + fee);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();

        e = escrow.getEscrow(escrowId);
        assertTrue(e.state == SardisEscrow.EscrowState.Funded);
        console.log("  Escrow funded, state: Funded");

        // Step 3: Seller confirms delivery
        console.log("Step 3: Seller confirming delivery...");
        vm.prank(agent2);
        escrow.confirmDelivery(escrowId);
        console.log("  Delivery confirmed by seller");

        // Step 4: Buyer approves release
        console.log("Step 4: Buyer approving release...");
        uint256 sellerBalanceBefore = usdc.balanceOf(agent2);
        uint256 sardisBalanceBefore = usdc.balanceOf(deployer);

        vm.prank(agent1);
        escrow.approveRelease(escrowId);

        e = escrow.getEscrow(escrowId);
        assertTrue(e.state == SardisEscrow.EscrowState.Released);
        assertEq(usdc.balanceOf(agent2), sellerBalanceBefore + escrowAmount);
        assertEq(usdc.balanceOf(deployer), sardisBalanceBefore + fee);
        console.log("  Funds released!");
        console.log("  Seller received:", escrowAmount / 10**6, "USDC");
        console.log("  Sardis fee:", fee / 10**6, "USDC");

        console.log("\n=== Escrow Flow Test PASSED ===\n");
    }

    // ============================================================
    // E2E Test 5: Escrow with Milestones
    // ============================================================
    function test_E2E_MilestoneEscrow() public {
        console.log("\n=== E2E Test: Milestone Escrow ===\n");

        uint256[] memory milestoneAmounts = new uint256[](3);
        milestoneAmounts[0] = 300 * 10**6;  // Phase 1: Design
        milestoneAmounts[1] = 500 * 10**6;  // Phase 2: Development
        milestoneAmounts[2] = 200 * 10**6;  // Phase 3: Testing

        uint256 totalAmount = 1000 * 10**6;
        uint256 fee = (totalAmount * FEE_BPS) / 10000;

        // Step 1: Create milestone escrow
        console.log("Step 1: Creating milestone escrow (3 phases)...");
        vm.prank(agent1);
        uint256 escrowId = escrow.createEscrowWithMilestones(
            agent2,
            address(usdc),
            milestoneAmounts,
            block.timestamp + 30 days,
            bytes32(0),
            "Software development project"
        );

        SardisEscrow.Milestone[] memory ms = escrow.getMilestones(escrowId);
        assertEq(ms.length, 3);
        console.log("  Created 3 milestones: 300, 500, 200 USDC");

        // Step 2: Fund escrow
        console.log("Step 2: Funding escrow...");
        vm.startPrank(agent1);
        usdc.approve(address(escrow), totalAmount + fee);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();

        // Step 3: Complete and release milestones one by one
        uint256 sellerBalance = usdc.balanceOf(agent2);

        for (uint256 i = 0; i < 3; i++) {
            console.log("Step", 3 + i, ": Processing milestone", i + 1);

            // Seller completes milestone
            vm.prank(agent2);
            escrow.completeMilestone(escrowId, i);
            console.log("    Seller marked milestone as complete");

            // Buyer releases milestone
            vm.prank(agent1);
            escrow.releaseMilestone(escrowId, i);

            uint256 expectedPayment = milestoneAmounts[i];
            sellerBalance += expectedPayment;
            assertEq(usdc.balanceOf(agent2), sellerBalance);
            console.log("    Buyer released", expectedPayment / 10**6, "USDC to seller");
        }

        // Verify escrow is now Released
        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertTrue(e.state == SardisEscrow.EscrowState.Released, "Escrow should be Released");
        console.log("\n  All milestones completed, escrow state: Released");

        console.log("\n=== Milestone Escrow Test PASSED ===\n");
    }

    // ============================================================
    // E2E Test 6: Dispute Resolution
    // ============================================================
    function test_E2E_DisputeResolution() public {
        console.log("\n=== E2E Test: Dispute Resolution ===\n");

        uint256 escrowAmount = 1000 * 10**6;
        uint256 fee = (escrowAmount * FEE_BPS) / 10000;

        // Setup: Create and fund escrow
        vm.prank(agent1);
        uint256 escrowId = escrow.createEscrow(
            agent2, address(usdc), escrowAmount,
            block.timestamp + 7 days, bytes32(0), "Disputed service"
        );

        vm.startPrank(agent1);
        usdc.approve(address(escrow), escrowAmount + fee);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();

        // Step 1: Seller claims delivery
        console.log("Step 1: Seller confirms delivery...");
        vm.prank(agent2);
        escrow.confirmDelivery(escrowId);

        // Step 2: Buyer disputes (unhappy with service)
        console.log("Step 2: Buyer raises dispute...");
        vm.prank(agent1);
        escrow.raiseDispute(escrowId);

        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertTrue(e.state == SardisEscrow.EscrowState.Disputed);
        console.log("  Escrow state: Disputed");

        // Step 3: Arbiter resolves - 70% to buyer, 30% to seller
        console.log("Step 3: Arbiter resolving dispute (70% buyer, 30% seller)...");
        uint256 buyerBefore = usdc.balanceOf(agent1);
        uint256 sellerBefore = usdc.balanceOf(agent2);

        vm.prank(arbiter);
        escrow.resolveDispute(escrowId, 70); // 70% to buyer

        uint256 buyerAmount = (escrowAmount * 70) / 100;
        uint256 sellerAmount = escrowAmount - buyerAmount;

        assertEq(usdc.balanceOf(agent1), buyerBefore + buyerAmount);
        assertEq(usdc.balanceOf(agent2), sellerBefore + sellerAmount);
        console.log("  Buyer received:", buyerAmount / 10**6, "USDC");
        console.log("  Seller received:", sellerAmount / 10**6, "USDC");
        console.log("  Sardis received fee:", fee / 10**6, "USDC");

        console.log("\n=== Dispute Resolution Test PASSED ===\n");
    }

    // ============================================================
    // E2E Test 7: Emergency Recovery
    // ============================================================
    function test_E2E_EmergencyRecovery() public {
        console.log("\n=== E2E Test: Emergency Recovery ===\n");

        // Setup: Create and fund wallet
        address walletAddr = factory.createWallet(agent1);
        SardisAgentWallet wallet = SardisAgentWallet(payable(walletAddr));
        usdc.transfer(walletAddr, 5000 * 10**6);

        // Step 1: Pause wallet (emergency)
        console.log("Step 1: Pausing wallet (emergency stop)...");
        vm.prank(agent1);
        wallet.pause();

        // Payments should fail when paused
        vm.prank(agent1);
        vm.expectRevert();
        wallet.pay(address(usdc), merchant, 100 * 10**6, "Should fail");
        console.log("  Payments blocked while paused");

        // Step 2: Recovery address withdraws funds
        console.log("Step 2: Recovery address withdrawing funds...");
        uint256 recoveryBefore = usdc.balanceOf(recovery);
        vm.prank(recovery);
        wallet.emergencyWithdraw(address(usdc));

        assertEq(usdc.balanceOf(recovery), recoveryBefore + 5000 * 10**6);
        assertEq(wallet.getBalance(address(usdc)), 0);
        console.log("  Recovery address received 5000 USDC");

        // Step 3: Only Sardis can unpause
        console.log("Step 3: Testing unpause permissions...");
        vm.prank(agent1);
        vm.expectRevert("Only Sardis");
        wallet.unpause();

        vm.prank(address(factory));
        wallet.unpause();
        console.log("  Wallet unpaused by Sardis");

        console.log("\n=== Emergency Recovery Test PASSED ===\n");
    }

    // ============================================================
    // E2E Test 8: Sardis Transfer (Platform Migration)
    // ============================================================
    function test_E2E_SardisTransfer() public {
        console.log("\n=== E2E Test: Sardis Transfer ===\n");

        address newSardis = address(0x9999);

        // Setup
        address walletAddr = factory.createWallet(agent1);
        SardisAgentWallet wallet = SardisAgentWallet(payable(walletAddr));
        usdc.transfer(walletAddr, 1000 * 10**6);

        console.log("Step 1: Current Sardis is factory:", address(factory));
        assertEq(wallet.sardis(), address(factory));

        // Step 2: Propose Sardis role transfer (two-step timelock)
        console.log("Step 2: Proposing Sardis role transfer...");
        vm.prank(address(factory));
        wallet.proposeSardisTransfer(newSardis);

        assertEq(wallet.pendingSardis(), newSardis);
        // Sardis hasn't changed yet
        assertEq(wallet.sardis(), address(factory));
        console.log("  Transfer proposed, pending:", newSardis);

        // Step 2b: Wait for timelock to expire
        console.log("Step 2b: Waiting for timelock (2 days)...");
        vm.warp(block.timestamp + 2 days);

        // Step 2c: Execute the transfer
        vm.prank(address(factory));
        wallet.executeSardisTransfer();

        assertEq(wallet.sardis(), newSardis);
        console.log("  New Sardis:", newSardis);

        // Step 3: Old Sardis can no longer control wallet
        console.log("Step 3: Verifying old Sardis has no control...");
        vm.prank(address(factory));
        vm.expectRevert("Only Sardis");
        wallet.setLimits(2000 * 10**6, 10000 * 10**6);
        console.log("  Old Sardis correctly rejected");

        // Step 4: New Sardis can control wallet
        console.log("Step 4: New Sardis setting new limits...");
        vm.prank(newSardis);
        wallet.setLimits(2000 * 10**6, 10000 * 10**6);

        assertEq(wallet.limitPerTx(), 2000 * 10**6);
        assertEq(wallet.dailyLimit(), 10000 * 10**6);
        console.log("  New limits set: 2000/tx, 10000/day");

        console.log("\n=== Sardis Transfer Test PASSED ===\n");
    }

    // ============================================================
    // E2E Test 9: Cancel Unfunded Escrow
    // ============================================================
    function test_E2E_CancelEscrow() public {
        console.log("\n=== E2E Test: Cancel Unfunded Escrow ===\n");

        // Step 1: Create escrow but don't fund it
        console.log("Step 1: Creating escrow...");
        vm.prank(agent1);
        uint256 escrowId = escrow.createEscrow(
            agent2, address(usdc), 1000 * 10**6,
            block.timestamp + 7 days, bytes32(0), "Will be cancelled"
        );

        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertTrue(e.state == SardisEscrow.EscrowState.Created);
        console.log("  Escrow created, state: Created");

        // Step 2: Cancel before funding
        console.log("Step 2: Buyer cancelling escrow...");
        vm.prank(agent1);
        escrow.cancelEscrow(escrowId);

        e = escrow.getEscrow(escrowId);
        assertTrue(e.state == SardisEscrow.EscrowState.Expired);
        console.log("  Escrow cancelled, state: Expired");

        // Step 3: Can't fund cancelled escrow
        console.log("Step 3: Verifying cancelled escrow cannot be funded...");
        vm.startPrank(agent1);
        usdc.approve(address(escrow), 1010 * 10**6);
        vm.expectRevert("Invalid state");
        escrow.fundEscrow(escrowId);
        vm.stopPrank();
        console.log("  Correctly rejected funding of cancelled escrow");

        console.log("\n=== Cancel Escrow Test PASSED ===\n");
    }

    // ============================================================
    // E2E Test 10: Deterministic Wallet Deployment
    // ============================================================
    function test_E2E_DeterministicWallet() public {
        console.log("\n=== E2E Test: Deterministic Wallet ===\n");

        bytes32 salt = keccak256("my-unique-salt");

        // Step 1: Predict address before deployment
        console.log("Step 1: Predicting wallet address...");
        address predicted = factory.predictWalletAddress(agent1, salt);
        console.log("  Predicted address:", predicted);

        // Step 2: Deploy deterministically
        console.log("Step 2: Deploying wallet with CREATE2...");
        address actual = factory.createWalletDeterministic(agent1, salt);
        console.log("  Actual address:", actual);

        assertEq(predicted, actual, "Addresses should match");
        console.log("  Addresses match!");

        // Step 3: Verify wallet is functional
        console.log("Step 3: Verifying wallet functionality...");
        SardisAgentWallet wallet = SardisAgentWallet(payable(actual));
        assertEq(wallet.agent(), agent1);
        assertTrue(factory.isValidWallet(actual));
        console.log("  Wallet is valid and functional");

        console.log("\n=== Deterministic Wallet Test PASSED ===\n");
    }
}
