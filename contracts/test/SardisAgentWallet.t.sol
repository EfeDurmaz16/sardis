// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SardisAgentWallet.sol";
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

contract SardisAgentWalletTest is Test {
    SardisAgentWallet wallet;
    MockUSDC usdc;
    
    address agent = address(0x1);
    address sardis = address(0x2);
    address recovery = address(0x3);
    address merchant1 = address(0x4);
    address merchant2 = address(0x5);
    
    uint256 limitPerTx = 1000 * 10**6;  // 1000 USDC
    uint256 dailyLimit = 5000 * 10**6;  // 5000 USDC
    
    event Payment(
        address indexed token,
        address indexed to,
        uint256 amount,
        bytes32 indexed txHash,
        string purpose
    );
    
    event HoldCreated(
        bytes32 indexed holdId,
        address indexed merchant,
        address token,
        uint256 amount,
        uint256 expiresAt
    );
    
    function setUp() public {
        wallet = new SardisAgentWallet(
            agent,
            sardis,
            recovery,
            limitPerTx,
            dailyLimit
        );
        usdc = new MockUSDC();
        
        // Fund wallet with USDC
        usdc.transfer(address(wallet), 10000 * 10**6);
    }
    
    // ============ Constructor Tests ============
    
    function testConstructorSetsValues() public view {
        assertEq(wallet.agent(), agent);
        assertEq(wallet.sardis(), sardis);
        assertEq(wallet.recoveryAddress(), recovery);
        assertEq(wallet.limitPerTx(), limitPerTx);
        assertEq(wallet.dailyLimit(), dailyLimit);
    }
    
    function testConstructorRevertsWithZeroAgent() public {
        vm.expectRevert("Invalid agent");
        new SardisAgentWallet(address(0), sardis, recovery, limitPerTx, dailyLimit);
    }
    
    function testConstructorRevertsWithZeroSardis() public {
        vm.expectRevert("Invalid sardis");
        new SardisAgentWallet(agent, address(0), recovery, limitPerTx, dailyLimit);
    }
    
    // ============ Payment Tests ============
    
    function testPaymentByAgent() public {
        uint256 amount = 100 * 10**6;
        
        vm.prank(agent);
        bytes32 txHash = wallet.pay(address(usdc), merchant1, amount, "Test payment");
        
        assertTrue(txHash != bytes32(0));
        assertEq(usdc.balanceOf(merchant1), amount);
        assertEq(wallet.spentToday(), amount);
    }
    
    function testPaymentBySardis() public {
        uint256 amount = 100 * 10**6;
        
        vm.prank(sardis);
        bytes32 txHash = wallet.pay(address(usdc), merchant1, amount, "Sardis initiated");
        
        assertTrue(txHash != bytes32(0));
        assertEq(usdc.balanceOf(merchant1), amount);
    }
    
    function testPaymentRevertsForNonAuthorized() public {
        uint256 amount = 100 * 10**6;
        
        vm.prank(merchant1);
        vm.expectRevert("Only agent or Sardis");
        wallet.pay(address(usdc), merchant2, amount, "Unauthorized");
    }
    
    function testPaymentRevertsExceedingPerTxLimit() public {
        uint256 amount = limitPerTx + 1;
        
        vm.prank(agent);
        vm.expectRevert("Exceeds per-tx limit");
        wallet.pay(address(usdc), merchant1, amount, "Too large");
    }
    
    function testPaymentRevertsExceedingDailyLimit() public {
        uint256 amount = 1000 * 10**6;
        
        // Make 5 payments of 1000 USDC (total 5000 = daily limit)
        for (uint256 i = 0; i < 5; i++) {
            vm.prank(agent);
            wallet.pay(address(usdc), merchant1, amount, "Payment");
        }
        
        // Next payment should fail
        vm.prank(agent);
        vm.expectRevert("Exceeds daily limit");
        wallet.pay(address(usdc), merchant1, amount, "Over limit");
    }
    
    function testDailyLimitResetsNextDay() public {
        uint256 amount = dailyLimit;
        
        vm.prank(agent);
        wallet.pay(address(usdc), merchant1, amount, "Full limit");
        
        // Warp to next day
        vm.warp(block.timestamp + 1 days);
        
        // Should be able to pay again
        vm.prank(agent);
        wallet.pay(address(usdc), merchant1, 100 * 10**6, "Next day");
        
        assertEq(wallet.spentToday(), 100 * 10**6);
    }
    
    // ============ Merchant Control Tests ============
    
    function testAllowlistMode() public {
        vm.prank(sardis);
        wallet.setAllowlistMode(true);
        
        vm.prank(sardis);
        wallet.allowMerchant(merchant1);
        
        // Payment to allowed merchant should work
        vm.prank(agent);
        wallet.pay(address(usdc), merchant1, 100 * 10**6, "Allowed");
        
        // Payment to non-allowed merchant should fail
        vm.prank(agent);
        vm.expectRevert("Merchant not allowed");
        wallet.pay(address(usdc), merchant2, 100 * 10**6, "Not allowed");
    }
    
    function testDenylistMode() public {
        vm.prank(sardis);
        wallet.denyMerchant(merchant1);
        
        vm.prank(agent);
        vm.expectRevert("Merchant denied");
        wallet.pay(address(usdc), merchant1, 100 * 10**6, "Denied");
        
        // Payment to non-denied merchant should work
        vm.prank(agent);
        wallet.pay(address(usdc), merchant2, 100 * 10**6, "Not denied");
    }
    
    function testRemoveMerchant() public {
        vm.prank(sardis);
        wallet.denyMerchant(merchant1);
        
        vm.prank(sardis);
        wallet.removeMerchant(merchant1);
        
        // Payment should now work
        vm.prank(agent);
        wallet.pay(address(usdc), merchant1, 100 * 10**6, "Removed from denylist");
    }
    
    // ============ Hold Tests ============
    
    function testCreateHold() public {
        uint256 amount = 500 * 10**6;
        uint256 duration = 1 days;
        
        vm.prank(agent);
        bytes32 holdId = wallet.createHold(merchant1, address(usdc), amount, duration);
        
        assertTrue(holdId != bytes32(0));
        
        (
            address hMerchant,
            address hToken,
            uint256 hAmount,
            ,
            uint256 hExpiresAt,
            bool hCaptured,
            bool hVoided
        ) = wallet.holds(holdId);
        
        assertEq(hMerchant, merchant1);
        assertEq(hToken, address(usdc));
        assertEq(hAmount, amount);
        assertTrue(hExpiresAt > block.timestamp);
        assertFalse(hCaptured);
        assertFalse(hVoided);
    }
    
    function testCaptureHold() public {
        uint256 amount = 500 * 10**6;
        uint256 captureAmount = 400 * 10**6;
        
        vm.prank(agent);
        bytes32 holdId = wallet.createHold(merchant1, address(usdc), amount, 1 days);
        
        uint256 merchantBalanceBefore = usdc.balanceOf(merchant1);
        
        vm.prank(agent);
        wallet.captureHold(holdId, captureAmount);
        
        assertEq(usdc.balanceOf(merchant1), merchantBalanceBefore + captureAmount);
        
        (,,,,,bool captured,) = wallet.holds(holdId);
        assertTrue(captured);
    }
    
    function testVoidHold() public {
        uint256 amount = 500 * 10**6;
        
        vm.prank(agent);
        bytes32 holdId = wallet.createHold(merchant1, address(usdc), amount, 1 days);
        
        vm.prank(agent);
        wallet.voidHold(holdId);
        
        (,,,,,,bool voided) = wallet.holds(holdId);
        assertTrue(voided);
    }
    
    function testHoldRevertsWithInvalidDuration() public {
        vm.prank(agent);
        vm.expectRevert("Invalid duration");
        wallet.createHold(merchant1, address(usdc), 100 * 10**6, 0);
        
        vm.prank(agent);
        vm.expectRevert("Invalid duration");
        wallet.createHold(merchant1, address(usdc), 100 * 10**6, 8 days);
    }
    
    function testCaptureHoldRevertsAfterExpiry() public {
        uint256 amount = 500 * 10**6;
        
        vm.prank(agent);
        bytes32 holdId = wallet.createHold(merchant1, address(usdc), amount, 1 hours);
        
        // Warp past expiry
        vm.warp(block.timestamp + 2 hours);
        
        vm.prank(agent);
        vm.expectRevert("Hold expired");
        wallet.captureHold(holdId, amount);
    }
    
    // ============ Limit Management Tests ============
    
    function testSetLimits() public {
        uint256 newLimitPerTx = 2000 * 10**6;
        uint256 newDailyLimit = 10000 * 10**6;
        
        vm.prank(sardis);
        wallet.setLimits(newLimitPerTx, newDailyLimit);
        
        assertEq(wallet.limitPerTx(), newLimitPerTx);
        assertEq(wallet.dailyLimit(), newDailyLimit);
    }
    
    function testSetLimitsOnlySardis() public {
        vm.prank(agent);
        vm.expectRevert("Only Sardis");
        wallet.setLimits(100, 100);
    }
    
    // ============ Emergency Functions ============
    
    function testPause() public {
        vm.prank(agent);
        wallet.pause();
        
        vm.prank(agent);
        vm.expectRevert();
        wallet.pay(address(usdc), merchant1, 100 * 10**6, "Should fail");
    }
    
    function testUnpauseOnlySardis() public {
        vm.prank(agent);
        wallet.pause();
        
        vm.prank(agent);
        vm.expectRevert("Only Sardis");
        wallet.unpause();
        
        vm.prank(sardis);
        wallet.unpause();
        
        // Should work now
        vm.prank(agent);
        wallet.pay(address(usdc), merchant1, 100 * 10**6, "Works again");
    }
    
    function testEmergencyWithdraw() public {
        uint256 walletBalance = usdc.balanceOf(address(wallet));
        
        vm.prank(recovery);
        wallet.emergencyWithdraw(address(usdc));
        
        assertEq(usdc.balanceOf(recovery), walletBalance);
        assertEq(usdc.balanceOf(address(wallet)), 0);
    }
    
    function testEmergencyWithdrawOnlyRecovery() public {
        vm.prank(agent);
        vm.expectRevert("Only recovery");
        wallet.emergencyWithdraw(address(usdc));
    }
    
    // ============ View Function Tests ============
    
    function testGetBalance() public view {
        assertEq(wallet.getBalance(address(usdc)), 10000 * 10**6);
    }
    
    function testGetRemainingDailyLimit() public {
        assertEq(wallet.getRemainingDailyLimit(), dailyLimit);
        
        vm.prank(agent);
        wallet.pay(address(usdc), merchant1, 1000 * 10**6, "Payment");
        
        assertEq(wallet.getRemainingDailyLimit(), dailyLimit - 1000 * 10**6);
    }
    
    function testCanPay() public {
        (bool allowed, string memory reason) = wallet.canPay(merchant1, 100 * 10**6);
        assertTrue(allowed);
        assertEq(reason, "");
        
        (allowed, reason) = wallet.canPay(merchant1, limitPerTx + 1);
        assertFalse(allowed);
        assertEq(reason, "Exceeds per-transaction limit");
    }
}


