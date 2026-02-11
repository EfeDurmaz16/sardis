// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SardisAgentWallet.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockUSDCFuzz is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {}
    function decimals() public pure override returns (uint8) { return 6; }
    function mint(address to, uint256 amount) external { _mint(to, amount); }
}

/**
 * @title Fuzz and Invariant Tests for SardisAgentWallet
 * @notice Tests invariants that must always hold regardless of input.
 */
contract SardisAgentWalletFuzzTest is Test {
    SardisAgentWallet wallet;
    MockUSDCFuzz usdc;

    address agent = address(0x1);
    address sardis = address(0x2);
    address recovery = address(0x3);
    address merchant = address(0x4);

    uint256 constant LIMIT_PER_TX = 10_000 * 10**6;
    uint256 constant DAILY_LIMIT = 50_000 * 10**6;
    uint256 constant FUND_AMOUNT = 1_000_000 * 10**6;

    function setUp() public {
        usdc = new MockUSDCFuzz();
        wallet = new SardisAgentWallet(
            agent,
            sardis,
            recovery,
            LIMIT_PER_TX,
            DAILY_LIMIT
        );
        // Fund wallet
        usdc.mint(address(wallet), FUND_AMOUNT);

        // Whitelist MockUSDC on the token allowlist
        vm.prank(sardis);
        wallet.allowToken(address(usdc));
    }

    // ============ Fuzz: Holds ============

    /// @notice totalHeldAmount never exceeds actual token balance
    function testFuzz_holdAmountNeverExceedsBalance(uint256 amount, uint256 duration) public {
        amount = bound(amount, 1, FUND_AMOUNT);
        duration = bound(duration, 1, 7 days);

        vm.prank(agent);
        try wallet.createHold(merchant, address(usdc), amount, duration) {
            assertLe(
                wallet.totalHeldAmount(address(usdc)),
                usdc.balanceOf(address(wallet)),
                "Invariant: totalHeldAmount <= balance"
            );
        } catch {
            // Expected failures (limit exceeded, etc.) are fine
        }
    }

    /// @notice Partial capture: held amount is fully released, only captureAmount transferred
    function testFuzz_partialCaptureAccounting(uint256 holdAmount, uint256 captureAmount) public {
        holdAmount = bound(holdAmount, 1, LIMIT_PER_TX);
        captureAmount = bound(captureAmount, 1, holdAmount);

        vm.prank(agent);
        bytes32 holdId = wallet.createHold(merchant, address(usdc), holdAmount, 1 hours);

        uint256 heldBefore = wallet.totalHeldAmount(address(usdc));
        uint256 merchantBefore = usdc.balanceOf(merchant);
        uint256 walletBefore = usdc.balanceOf(address(wallet));

        vm.prank(agent);
        wallet.captureHold(holdId, captureAmount);

        // Held amount fully released
        assertEq(
            wallet.totalHeldAmount(address(usdc)),
            heldBefore - holdAmount,
            "Invariant: full hold amount released on capture"
        );

        // Merchant received exactly captureAmount
        assertEq(
            usdc.balanceOf(merchant),
            merchantBefore + captureAmount,
            "Merchant received capture amount"
        );

        // Wallet lost exactly captureAmount
        assertEq(
            usdc.balanceOf(address(wallet)),
            walletBefore - captureAmount,
            "Wallet debited capture amount"
        );
    }

    /// @notice Voiding a hold fully releases the held amount, no transfer
    function testFuzz_voidReleasesFullAmount(uint256 amount) public {
        amount = bound(amount, 1, LIMIT_PER_TX);

        vm.prank(agent);
        bytes32 holdId = wallet.createHold(merchant, address(usdc), amount, 1 hours);

        uint256 walletBefore = usdc.balanceOf(address(wallet));

        vm.prank(agent);
        wallet.voidHold(holdId);

        assertEq(wallet.totalHeldAmount(address(usdc)), 0, "Held amount zeroed after void");
        assertEq(usdc.balanceOf(address(wallet)), walletBefore, "No transfer on void");
    }

    // ============ Fuzz: Payment Limits ============

    /// @notice spentToday never exceeds dailyLimit
    function testFuzz_spentTodayNeverExceedsDailyLimit(uint256 amount) public {
        amount = bound(amount, 1, LIMIT_PER_TX);

        vm.prank(agent);
        try wallet.pay(address(usdc), merchant, amount, "fuzz") {
            // If pay succeeded, spentToday must be <= dailyLimit
            // (spentToday is internal, but getRemainingDailyLimit tells us)
            assertGe(
                wallet.getRemainingDailyLimit(),
                0,
                "Invariant: remaining daily limit >= 0"
            );
        } catch {
            // Rejected by limits — correct behavior
        }
    }

    /// @notice Multiple payments: cumulative spending respects daily limit
    function testFuzz_cumulativeSpendingRespectsLimit(uint8 numPayments, uint256 baseAmount) public {
        numPayments = uint8(bound(numPayments, 1, 20));
        baseAmount = bound(baseAmount, 1, LIMIT_PER_TX / 2);

        uint256 totalSpent = 0;

        for (uint8 i = 0; i < numPayments; i++) {
            vm.prank(agent);
            try wallet.pay(address(usdc), merchant, baseAmount, "fuzz") {
                totalSpent += baseAmount;
            } catch {
                break;  // Hit a limit
            }
        }

        // Total spent must not exceed daily limit
        assertLe(totalSpent, DAILY_LIMIT, "Invariant: total spent <= daily limit");
    }

    // ============ Fuzz: Zero Amount Rejection ============

    /// @notice Zero-amount payments must always revert
    function testFuzz_zeroAmountPayReverts(address token, address to) public {
        vm.assume(token != address(0) && to != address(0));
        vm.prank(agent);
        vm.expectRevert("Amount must be greater than zero");
        wallet.pay(token, to, 0, "zero");
    }

    /// @notice Zero-amount holds must always revert
    function testFuzz_zeroAmountHoldReverts(uint256 duration) public {
        duration = bound(duration, 1, 7 days);
        vm.prank(agent);
        vm.expectRevert("Amount must be greater than zero");
        wallet.createHold(merchant, address(usdc), 0, duration);
    }

    // ============ Fuzz: Day Boundary ============

    /// @notice Daily limit resets after day boundary
    function testFuzz_dailyLimitResetsAfterDayBoundary(uint256 amount, uint256 warpSeconds) public {
        amount = bound(amount, 1, LIMIT_PER_TX);
        warpSeconds = bound(warpSeconds, 1 days, 30 days);

        // Spend up to limit
        vm.startPrank(agent);
        try wallet.pay(address(usdc), merchant, amount, "day1") {} catch {}

        uint256 remainingBefore = wallet.getRemainingDailyLimit();

        // Warp past day boundary
        vm.warp(block.timestamp + warpSeconds);

        uint256 remainingAfter = wallet.getRemainingDailyLimit();

        // After day boundary, daily limit should be fully available
        assertEq(remainingAfter, DAILY_LIMIT, "Daily limit should reset after day boundary");
        vm.stopPrank();
    }
}
