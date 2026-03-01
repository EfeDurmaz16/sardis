// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "./SardisEscrow.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

// Mock ERC20 token for testing
contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {
        _mint(msg.sender, 1_000_000 * 10**6);
    }
    
    function decimals() public pure override returns (uint8) {
        return 6;
    }
    
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract GovernanceExecutorMock {}

contract SardisEscrowTest is Test {
    SardisEscrow escrow;
    MockUSDC usdc;
    
    address deployer = address(this);
    address arbiter = address(0x1);
    address buyer = address(0x2);
    address seller = address(0x3);
    
    uint256 feeBps = 100;           // 1%
    uint256 minAmount = 10 * 10**6; // 10 USDC
    uint256 maxDeadlineDays = 30;
    
    event EscrowCreated(
        uint256 indexed escrowId,
        address indexed buyer,
        address indexed seller,
        address token,
        uint256 amount
    );
    
    event EscrowFunded(uint256 indexed escrowId);
    event EscrowReleased(uint256 indexed escrowId, uint256 amountToSeller, uint256 fee);
    event EscrowRefunded(uint256 indexed escrowId);
    event DisputeRaised(uint256 indexed escrowId, address indexed by);
    event DisputeResolved(uint256 indexed escrowId, uint256 buyerAmount, uint256 sellerAmount);
    
    function setUp() public {
        escrow = new SardisEscrow(arbiter, feeBps, minAmount, maxDeadlineDays);
        usdc = new MockUSDC();
        
        // Give buyer some USDC
        usdc.transfer(buyer, 100000 * 10**6);
    }
    
    // ============ Constructor Tests ============
    
    function testConstructorSetsValues() public view {
        assertEq(escrow.arbiter(), arbiter);
        assertEq(escrow.feeBps(), feeBps);
        assertEq(escrow.minAmount(), minAmount);
        assertEq(escrow.maxDeadlineDays(), maxDeadlineDays);
    }
    
    function testConstructorRevertsWithZeroArbiter() public {
        vm.expectRevert("Invalid arbiter");
        new SardisEscrow(address(0), feeBps, minAmount, maxDeadlineDays);
    }
    
    function testConstructorRevertsWithHighFee() public {
        vm.expectRevert("Fee too high");
        new SardisEscrow(arbiter, 501, minAmount, maxDeadlineDays);
    }
    
    // ============ Escrow Creation Tests ============
    
    function testCreateEscrow() public {
        uint256 amount = 1000 * 10**6;
        uint256 deadline = block.timestamp + 7 days;
        bytes32 conditionHash = keccak256("delivery_conditions");
        
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller,
            address(usdc),
            amount,
            deadline,
            conditionHash,
            "Test service"
        );
        
        assertEq(escrowId, 0);
        assertEq(escrow.getEscrowCount(), 1);
        
        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertEq(e.buyer, buyer);
        assertEq(e.seller, seller);
        assertEq(e.token, address(usdc));
        assertEq(e.amount, amount);
        assertEq(e.deadline, deadline);
        assertEq(uint(e.state), uint(SardisEscrow.EscrowState.Created));
    }
    
    function testCreateEscrowRevertsWithSelfAsSeller() public {
        vm.prank(buyer);
        vm.expectRevert("Invalid seller");
        escrow.createEscrow(
            buyer, // Self as seller
            address(usdc),
            1000 * 10**6,
            block.timestamp + 7 days,
            bytes32(0),
            "Test"
        );
    }
    
    function testCreateEscrowRevertsWithLowAmount() public {
        vm.prank(buyer);
        vm.expectRevert("Amount too low");
        escrow.createEscrow(
            seller,
            address(usdc),
            1 * 10**6, // Below minimum
            block.timestamp + 7 days,
            bytes32(0),
            "Test"
        );
    }
    
    function testCreateEscrowRevertsWithPastDeadline() public {
        vm.prank(buyer);
        vm.expectRevert("Invalid deadline");
        escrow.createEscrow(
            seller,
            address(usdc),
            1000 * 10**6,
            block.timestamp - 1, // Past deadline
            bytes32(0),
            "Test"
        );
    }
    
    function testCreateEscrowRevertsWithFarDeadline() public {
        vm.prank(buyer);
        vm.expectRevert("Deadline too far");
        escrow.createEscrow(
            seller,
            address(usdc),
            1000 * 10**6,
            block.timestamp + 31 days, // Beyond max
            bytes32(0),
            "Test"
        );
    }
    
    // ============ Funding Tests ============
    
    function testFundEscrow() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        uint256 totalRequired = amount + fee;
        
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 7 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), totalRequired);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();
        
        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertEq(uint(e.state), uint(SardisEscrow.EscrowState.Funded));
        assertEq(usdc.balanceOf(address(escrow)), totalRequired);
    }
    
    function testFundEscrowRevertsForNonBuyer() public {
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), 1000 * 10**6, block.timestamp + 7 days, bytes32(0), "Test"
        );
        
        vm.prank(seller);
        vm.expectRevert("Only buyer");
        escrow.fundEscrow(escrowId);
    }
    
    // ============ Release Flow Tests ============
    
    function testReleaseFlow() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        
        // Create and fund
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 7 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), amount + fee);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();
        
        // Seller confirms delivery
        vm.prank(seller);
        escrow.confirmDelivery(escrowId);
        
        // Buyer approves release
        uint256 sellerBalanceBefore = usdc.balanceOf(seller);
        uint256 ownerBalanceBefore = usdc.balanceOf(deployer);
        
        vm.prank(buyer);
        escrow.approveRelease(escrowId);
        
        // Should auto-release since both approved
        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertEq(uint(e.state), uint(SardisEscrow.EscrowState.Released));
        assertEq(usdc.balanceOf(seller), sellerBalanceBefore + amount);
        assertEq(usdc.balanceOf(deployer), ownerBalanceBefore + fee);
    }
    
    function testManualRelease() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        
        // Create and fund
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 7 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), amount + fee);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();
        
        // Buyer approves first
        vm.prank(buyer);
        escrow.approveRelease(escrowId);
        
        // Seller confirms delivery
        vm.prank(seller);
        escrow.confirmDelivery(escrowId);
        
        // Manual release
        escrow.release(escrowId);
        
        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertEq(uint(e.state), uint(SardisEscrow.EscrowState.Released));
    }
    
    // ============ Refund Tests ============
    
    function testRefundAfterDeadline() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        uint256 total = amount + fee;
        
        // Create and fund
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 1 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), total);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();
        
        uint256 buyerBalanceBefore = usdc.balanceOf(buyer);
        
        // Warp past deadline
        vm.warp(block.timestamp + 2 days);
        
        vm.prank(buyer);
        escrow.refund(escrowId);
        
        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertEq(uint(e.state), uint(SardisEscrow.EscrowState.Refunded));
        assertEq(usdc.balanceOf(buyer), buyerBalanceBefore + total);
    }
    
    function testRefundRevertsIfSellerConfirmed() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 1 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), amount + fee);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();
        
        vm.prank(seller);
        escrow.confirmDelivery(escrowId);
        
        vm.warp(block.timestamp + 2 days);
        
        vm.prank(buyer);
        vm.expectRevert("Seller already confirmed");
        escrow.refund(escrowId);
    }
    
    // ============ Dispute Tests ============
    
    function testRaiseDispute() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 7 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), amount + fee);
        escrow.fundEscrow(escrowId);
        escrow.raiseDispute(escrowId);
        vm.stopPrank();
        
        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertEq(uint(e.state), uint(SardisEscrow.EscrowState.Disputed));
    }
    
    function testSellerCanRaiseDispute() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 7 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), amount + fee);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();
        
        vm.prank(seller);
        escrow.raiseDispute(escrowId);
        
        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertEq(uint(e.state), uint(SardisEscrow.EscrowState.Disputed));
    }
    
    function testResolveDisputeFullToBuyer() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 7 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), amount + fee);
        escrow.fundEscrow(escrowId);
        escrow.raiseDispute(escrowId);
        vm.stopPrank();
        
        uint256 buyerBalanceBefore = usdc.balanceOf(buyer);
        
        vm.prank(arbiter);
        escrow.resolveDispute(escrowId, 100); // 100% to buyer
        
        SardisEscrow.Escrow memory e = escrow.getEscrow(escrowId);
        assertEq(uint(e.state), uint(SardisEscrow.EscrowState.Resolved));
        assertEq(usdc.balanceOf(buyer), buyerBalanceBefore + amount);
    }
    
    function testResolveDisputeSplit() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 7 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), amount + fee);
        escrow.fundEscrow(escrowId);
        escrow.raiseDispute(escrowId);
        vm.stopPrank();
        
        uint256 buyerBalanceBefore = usdc.balanceOf(buyer);
        uint256 sellerBalanceBefore = usdc.balanceOf(seller);
        
        vm.prank(arbiter);
        escrow.resolveDispute(escrowId, 50); // 50-50 split
        
        assertEq(usdc.balanceOf(buyer), buyerBalanceBefore + amount / 2);
        assertEq(usdc.balanceOf(seller), sellerBalanceBefore + amount / 2);
    }
    
    function testResolveDisputeOnlyArbiter() public {
        uint256 amount = 1000 * 10**6;
        uint256 fee = (amount * feeBps) / 10000;
        
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrow(
            seller, address(usdc), amount, block.timestamp + 7 days, bytes32(0), "Test"
        );
        
        vm.startPrank(buyer);
        usdc.approve(address(escrow), amount + fee);
        escrow.fundEscrow(escrowId);
        escrow.raiseDispute(escrowId);
        vm.stopPrank();
        
        vm.prank(buyer);
        vm.expectRevert("Only arbiter");
        escrow.resolveDispute(escrowId, 100);
    }
    
    // ============ Milestone Tests ============
    
    function testCreateEscrowWithMilestones() public {
        uint256[] memory milestoneAmounts = new uint256[](3);
        milestoneAmounts[0] = 200 * 10**6;
        milestoneAmounts[1] = 300 * 10**6;
        milestoneAmounts[2] = 500 * 10**6;
        
        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrowWithMilestones(
            seller,
            address(usdc),
            milestoneAmounts,
            block.timestamp + 7 days,
            bytes32(0),
            "Milestone service"
        );
        
        SardisEscrow.Milestone[] memory m = escrow.getMilestones(escrowId);
        assertEq(m.length, 3);
        assertEq(m[0].amount, 200 * 10**6);
        assertEq(m[1].amount, 300 * 10**6);
        assertEq(m[2].amount, 500 * 10**6);
    }
    
    function testReleaseMilestone() public {
        uint256[] memory milestoneAmounts = new uint256[](2);
        milestoneAmounts[0] = 500 * 10**6;
        milestoneAmounts[1] = 500 * 10**6;

        uint256 totalAmount = 1000 * 10**6;
        uint256 fee = (totalAmount * feeBps) / 10000;

        vm.prank(buyer);
        uint256 escrowId = escrow.createEscrowWithMilestones(
            seller, address(usdc), milestoneAmounts, block.timestamp + 7 days, bytes32(0), "Test"
        );

        vm.startPrank(buyer);
        usdc.approve(address(escrow), totalAmount + fee);
        escrow.fundEscrow(escrowId);
        vm.stopPrank();

        // Seller completes first milestone
        vm.prank(seller);
        escrow.completeMilestone(escrowId, 0);

        uint256 sellerBalanceBefore = usdc.balanceOf(seller);
        uint256 ownerBalanceBefore = usdc.balanceOf(deployer);

        // Buyer releases first milestone
        vm.prank(buyer);
        escrow.releaseMilestone(escrowId, 0);

        // Seller gets full milestone amount (fee was paid by buyer upfront)
        assertEq(usdc.balanceOf(seller), sellerBalanceBefore + 500 * 10**6);

        // Owner (Sardis) gets proportional fee from the deposited fee
        uint256 expectedFee = (500 * 10**6 * fee) / totalAmount; // proportional fee
        assertEq(usdc.balanceOf(deployer), ownerBalanceBefore + expectedFee);
    }
    
    // ============ Admin Tests ============
    
    function testSetArbiter() public {
        address newArbiter = address(0x999);

        escrow.setArbiter(newArbiter);
        assertEq(escrow.pendingArbiter(), newArbiter);
        assertEq(escrow.arbiter(), arbiter); // unchanged before timelock

        vm.warp(block.timestamp + escrow.ARBITER_UPDATE_TIMELOCK());
        escrow.executeArbiterUpdate();

        assertEq(escrow.arbiter(), newArbiter);
        assertEq(escrow.pendingArbiter(), address(0));
    }

    function testSetArbiterRevertsBeforeTimelock() public {
        address newArbiter = address(0x999);
        escrow.setArbiter(newArbiter);

        vm.expectRevert("Timelock not expired");
        escrow.executeArbiterUpdate();
    }

    function testCancelPendingArbiterUpdate() public {
        address newArbiter = address(0x999);
        escrow.setArbiter(newArbiter);
        assertEq(escrow.pendingArbiter(), newArbiter);

        escrow.cancelArbiterUpdate();
        assertEq(escrow.pendingArbiter(), address(0));
        assertEq(escrow.pendingArbiterEta(), 0);
        assertEq(escrow.arbiter(), arbiter);
    }
    
    function testSetFeeBps() public {
        uint256 newFee = 200; // 2%
        escrow.setFeeBps(newFee);
        assertEq(escrow.feeBps(), newFee);
    }
    
    function testSetFeeBpsRevertsIfTooHigh() public {
        vm.expectRevert("Fee too high");
        escrow.setFeeBps(501);
    }

    function testGovernanceExecutorCanMutateTimelockedArbiter() public {
        GovernanceExecutorMock governance = new GovernanceExecutorMock();
        address governanceAddr = address(governance);
        address newArbiter = address(0x888);

        escrow.setGovernanceExecutor(governanceAddr);
        assertEq(escrow.governanceExecutor(), governanceAddr);

        vm.prank(governanceAddr);
        escrow.proposeArbiter(newArbiter);
        assertEq(escrow.pendingArbiter(), newArbiter);

        vm.warp(block.timestamp + escrow.ARBITER_UPDATE_TIMELOCK());
        vm.prank(governanceAddr);
        escrow.executeArbiterUpdate();

        assertEq(escrow.arbiter(), newArbiter);
        assertEq(escrow.pendingArbiter(), address(0));
    }

    function testOnlyOwnerCanSetGovernanceExecutor() public {
        GovernanceExecutorMock governance = new GovernanceExecutorMock();
        vm.prank(buyer);
        vm.expectRevert();
        escrow.setGovernanceExecutor(address(governance));
    }

    function testSetGovernanceExecutorRevertsForEOA() public {
        vm.expectRevert("Executor must be contract");
        escrow.setGovernanceExecutor(address(0xA11CE));
    }

    function testNonGovernanceAdminCannotRunAdminUpdates() public {
        GovernanceExecutorMock governance = new GovernanceExecutorMock();
        escrow.setGovernanceExecutor(address(governance));

        vm.prank(seller);
        vm.expectRevert("Only governance admin");
        escrow.setFeeBps(150);
    }

    function testEnableGovernanceStrictModeRequiresContractExecutor() public {
        vm.expectRevert("Executor required");
        escrow.enableGovernanceStrictMode();
    }

    function testStrictModeBlocksOwnerGovernanceBypass() public {
        GovernanceExecutorMock governance = new GovernanceExecutorMock();
        escrow.setGovernanceExecutor(address(governance));
        escrow.enableGovernanceStrictMode();

        vm.expectRevert("Only governance executor");
        escrow.setFeeBps(150);
    }

    function testStrictModeAllowsExecutorGovernanceActions() public {
        GovernanceExecutorMock governance = new GovernanceExecutorMock();
        address governanceAddr = address(governance);
        escrow.setGovernanceExecutor(governanceAddr);
        escrow.enableGovernanceStrictMode();

        vm.prank(governanceAddr);
        escrow.setFeeBps(150);

        assertEq(escrow.feeBps(), 150);
    }

    function testTimelockedGovernanceExecutorUpdate() public {
        GovernanceExecutorMock governance = new GovernanceExecutorMock();
        GovernanceExecutorMock nextGovernance = new GovernanceExecutorMock();

        escrow.setGovernanceExecutor(address(governance));
        escrow.enableGovernanceStrictMode();

        vm.prank(address(governance));
        escrow.proposeGovernanceExecutor(address(nextGovernance));
        assertEq(escrow.pendingGovernanceExecutor(), address(nextGovernance));

        vm.expectRevert("Timelock not expired");
        vm.prank(address(governance));
        escrow.executeGovernanceExecutorUpdate();

        vm.warp(block.timestamp + escrow.GOVERNANCE_EXECUTOR_UPDATE_TIMELOCK());
        vm.prank(address(governance));
        escrow.executeGovernanceExecutorUpdate();

        assertEq(escrow.governanceExecutor(), address(nextGovernance));
        assertEq(escrow.pendingGovernanceExecutor(), address(0));
        assertEq(escrow.pendingGovernanceExecutorEta(), 0);
    }

    function testSetGovernanceExecutorBlockedInStrictMode() public {
        GovernanceExecutorMock governance = new GovernanceExecutorMock();
        GovernanceExecutorMock nextGovernance = new GovernanceExecutorMock();
        escrow.setGovernanceExecutor(address(governance));
        escrow.enableGovernanceStrictMode();

        vm.expectRevert("Use timelocked executor update");
        escrow.setGovernanceExecutor(address(nextGovernance));
    }

    function testOwnershipTransferIsTimelocked() public {
        address newOwner = address(0xBEEF);
        escrow.transferOwnership(newOwner);
        assertEq(escrow.pendingOwner(), newOwner);
        assertEq(escrow.owner(), address(this));

        vm.warp(block.timestamp + escrow.OWNERSHIP_TRANSFER_TIMELOCK());
        escrow.executeOwnershipTransfer();

        assertEq(escrow.owner(), newOwner);
        assertEq(escrow.pendingOwner(), address(0));
        assertEq(escrow.ownershipTransferEta(), 0);
    }

    function testOwnershipTransferRevertsBeforeTimelock() public {
        address newOwner = address(0xBEEF);
        escrow.transferOwnership(newOwner);

        vm.expectRevert("Timelock not expired");
        escrow.executeOwnershipTransfer();
    }

    function testCancelOwnershipTransfer() public {
        address newOwner = address(0xBEEF);
        escrow.transferOwnership(newOwner);
        assertEq(escrow.pendingOwner(), newOwner);

        escrow.cancelOwnershipTransfer();
        assertEq(escrow.pendingOwner(), address(0));
        assertEq(escrow.ownershipTransferEta(), 0);
        assertEq(escrow.owner(), address(this));
    }

    function testOwnershipTransferInStrictModeRequiresGovernanceExecutor() public {
        GovernanceExecutorMock governance = new GovernanceExecutorMock();
        escrow.setGovernanceExecutor(address(governance));
        escrow.enableGovernanceStrictMode();

        vm.expectRevert("Only governance executor");
        escrow.transferOwnership(address(0xBEEF));

        vm.prank(address(governance));
        escrow.transferOwnership(address(0xBEEF));
        assertEq(escrow.pendingOwner(), address(0xBEEF));

        vm.warp(block.timestamp + escrow.OWNERSHIP_TRANSFER_TIMELOCK());
        vm.prank(address(governance));
        escrow.executeOwnershipTransfer();

        assertEq(escrow.owner(), address(0xBEEF));
    }
}


