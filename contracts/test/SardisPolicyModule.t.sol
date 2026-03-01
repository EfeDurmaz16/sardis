// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SardisPolicyModule.sol";

contract SardisPolicyModuleTest is Test {
    SardisPolicyModule internal module;

    address internal sardis = address(this);
    address internal safe1 = address(0xBEEF);
    address internal merchant1 = address(0xCAFE);
    address internal merchant2 = address(0xDEAD);
    address internal usdc = address(0xA0b8);
    address internal weth = address(0xC02a);
    address internal notSardis = address(0x9999);

    uint256 internal constant LIMIT_PER_TX = 1000e6; // $1,000 USDC
    uint256 internal constant DAILY_LIMIT = 5000e6; // $5,000 USDC

    function setUp() public {
        module = new SardisPolicyModule(sardis);
    }

    // ============ Constructor ============

    function testConstructorSetsSardis() public view {
        assertEq(module.sardis(), sardis);
    }

    function testConstructorRevertsZeroAddress() public {
        vm.expectRevert("Invalid sardis");
        new SardisPolicyModule(address(0));
    }

    // ============ Wallet Initialization ============

    function testInitializeWallet() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);

        SardisPolicyModule.WalletPolicy memory p = module.getPolicy(safe1);
        assertTrue(p.initialized);
        assertEq(p.limitPerTx, LIMIT_PER_TX);
        assertEq(p.dailyLimit, DAILY_LIMIT);
        assertEq(p.coSignLimitPerTx, LIMIT_PER_TX * 10);
        assertEq(p.coSignDailyLimit, DAILY_LIMIT * 10);
        assertFalse(p.useAllowlist);
        assertTrue(p.enforceTokenAllowlist);
        assertFalse(p.paused);
    }

    function testInitializeWalletEmitsEvent() public {
        vm.expectEmit(true, false, false, true);
        emit SardisPolicyModule.WalletInitialized(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
    }

    function testInitializeWalletRevertsIfAlreadyInitialized() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        vm.expectRevert("Already initialized");
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
    }

    function testInitializeWalletRevertsZeroAddress() public {
        vm.expectRevert("Invalid safe");
        module.initializeWallet(address(0), LIMIT_PER_TX, DAILY_LIMIT);
    }

    function testInitializeWalletRevertsIfNotSardis() public {
        vm.prank(notSardis);
        vm.expectRevert("Only Sardis");
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
    }

    // ============ checkTransaction — ETH value ============

    function testCheckTransactionETHWithinLimits() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        module.checkTransaction(safe1, merchant1, 0.5 ether, "");
    }

    function testCheckTransactionETHExceedsPerTx() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        vm.expectRevert("Exceeds per-tx limit");
        module.checkTransaction(safe1, merchant1, 2 ether, "");
    }

    function testCheckTransactionETHExceedsDailyLimit() public {
        module.initializeWallet(safe1, 3 ether, 5 ether);
        module.checkTransaction(safe1, merchant1, 3 ether, "");
        vm.expectRevert("Exceeds daily limit");
        module.checkTransaction(safe1, merchant1, 3 ether, "");
    }

    // ============ checkTransaction — ERC-20 transfer ============

    function testCheckTransactionERC20Transfer() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        module.allowToken(safe1, usdc);

        bytes memory data = abi.encodeWithSelector(0xa9059cbb, merchant1, 500e6);
        module.checkTransaction(safe1, usdc, 0, data);
    }

    function testCheckTransactionERC20TransferExceedsLimit() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        module.allowToken(safe1, usdc);

        bytes memory data = abi.encodeWithSelector(0xa9059cbb, merchant1, 2000e6);
        vm.expectRevert("Exceeds per-tx limit");
        module.checkTransaction(safe1, usdc, 0, data);
    }

    function testCheckTransactionERC20TokenNotAllowed() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        // Token not added to allowlist

        bytes memory data = abi.encodeWithSelector(0xa9059cbb, merchant1, 100e6);
        vm.expectRevert("Token not allowed");
        module.checkTransaction(safe1, usdc, 0, data);
    }

    function testCheckTransactionERC20ApproveAlsoChecked() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        module.allowToken(safe1, usdc);

        bytes memory data = abi.encodeWithSelector(0x095ea7b3, merchant1, 500e6);
        module.checkTransaction(safe1, usdc, 0, data);

        assertEq(module.spentToday(safe1), 500e6);
    }

    // ============ checkTransaction — Paused ============

    function testCheckTransactionRevertsWhenPaused() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        module.pause(safe1);

        vm.expectRevert("Wallet paused");
        module.checkTransaction(safe1, merchant1, 0.5 ether, "");
    }

    // ============ checkTransaction — Not initialized ============

    function testCheckTransactionRevertsIfNotInitialized() public {
        vm.expectRevert("Wallet not initialized");
        module.checkTransaction(safe1, merchant1, 0.5 ether, "");
    }

    // ============ Co-Signed Transaction ============

    function testCoSignedTransactionElevatedLimits() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        // Normal limit is 1 ETH, co-sign is 10 ETH
        module.checkCoSignedTransaction(safe1, merchant1, 5 ether, "");
    }

    function testCoSignedTransactionExceedsCoSignLimit() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        // Co-sign per-tx is 10 ETH
        vm.expectRevert("Exceeds co-sign per-tx limit");
        module.checkCoSignedTransaction(safe1, merchant1, 11 ether, "");
    }

    function testCoSignedTransactionOnlySardis() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        vm.prank(notSardis);
        vm.expectRevert("Only Sardis");
        module.checkCoSignedTransaction(safe1, merchant1, 0.5 ether, "");
    }

    function testCoSignedTransactionRevertsWhenPaused() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        module.pause(safe1);
        vm.expectRevert("Wallet paused");
        module.checkCoSignedTransaction(safe1, merchant1, 0.5 ether, "");
    }

    // ============ Daily Limit Reset ============

    function testDailyLimitResetsNextDay() public {
        module.initializeWallet(safe1, 3 ether, 5 ether);
        module.checkTransaction(safe1, merchant1, 3 ether, "");
        assertEq(module.spentToday(safe1), 3 ether);

        // Warp forward 1 day
        vm.warp(block.timestamp + 1 days);
        module.checkTransaction(safe1, merchant1, 3 ether, "");
        // Spent should be reset to just the new amount
        assertEq(module.spentToday(safe1), 3 ether);
    }

    function testGetRemainingDailyLimit() public {
        module.initializeWallet(safe1, 3 ether, 5 ether);
        assertEq(module.getRemainingDailyLimit(safe1), 5 ether);

        module.checkTransaction(safe1, merchant1, 2 ether, "");
        assertEq(module.getRemainingDailyLimit(safe1), 3 ether);

        // After day passes, full limit available
        vm.warp(block.timestamp + 1 days);
        assertEq(module.getRemainingDailyLimit(safe1), 5 ether);
    }

    // ============ Merchant Allowlist / Denylist ============

    function testMerchantAllowlistBlocks() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        module.setAllowlistMode(safe1, true);

        vm.expectRevert("Merchant not allowed");
        module.checkTransaction(safe1, merchant1, 0.5 ether, "");
    }

    function testMerchantAllowlistAllows() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        module.setAllowlistMode(safe1, true);
        module.allowMerchant(safe1, merchant1);

        module.checkTransaction(safe1, merchant1, 0.5 ether, "");
    }

    function testMerchantDenylistBlocks() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        module.denyMerchant(safe1, merchant1);

        vm.expectRevert("Merchant denied");
        module.checkTransaction(safe1, merchant1, 0.5 ether, "");
    }

    function testRemoveMerchantClearsBoth() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        module.denyMerchant(safe1, merchant1);
        module.removeMerchant(safe1, merchant1);

        // Should work now
        module.checkTransaction(safe1, merchant1, 0.5 ether, "");
    }

    function testAllowMerchantClearsDeny() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);
        module.denyMerchant(safe1, merchant1);
        module.allowMerchant(safe1, merchant1);

        // Should work — allowMerchant clears deny
        module.checkTransaction(safe1, merchant1, 0.5 ether, "");
    }

    // ============ Token Allowlist ============

    function testTokenAllowlistEnforcedByDefault() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        SardisPolicyModule.WalletPolicy memory p = module.getPolicy(safe1);
        assertTrue(p.enforceTokenAllowlist);
    }

    function testAllowToken() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        module.allowToken(safe1, usdc);
        assertTrue(module.isTokenAllowed(safe1, usdc));
    }

    function testRemoveToken() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        module.allowToken(safe1, usdc);
        module.removeToken(safe1, usdc);
        assertFalse(module.isTokenAllowed(safe1, usdc));
    }

    function testDisableTokenAllowlist() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        module.setTokenAllowlistEnforced(safe1, false);

        // Any token should be allowed now
        assertTrue(module.isTokenAllowed(safe1, weth));
    }

    function testAllowTokenRevertsZeroAddress() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        vm.expectRevert("Invalid token");
        module.allowToken(safe1, address(0));
    }

    // ============ Policy Updates ============

    function testSetLimits() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        module.setLimits(safe1, 2000e6, 10000e6, 20000e6, 100000e6);

        SardisPolicyModule.WalletPolicy memory p = module.getPolicy(safe1);
        assertEq(p.limitPerTx, 2000e6);
        assertEq(p.dailyLimit, 10000e6);
        assertEq(p.coSignLimitPerTx, 20000e6);
        assertEq(p.coSignDailyLimit, 100000e6);
    }

    function testSetLimitsRevertsIfCoSignLessThanNormal() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        vm.expectRevert("Co-sign per-tx must be >= normal");
        module.setLimits(safe1, 2000e6, 10000e6, 1000e6, 100000e6);
    }

    function testSetLimitsRevertsIfCoSignDailyLessThanNormal() public {
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
        vm.expectRevert("Co-sign daily must be >= normal");
        module.setLimits(safe1, 2000e6, 10000e6, 20000e6, 5000e6);
    }

    // ============ Pause / Unpause ============

    function testPauseAndUnpause() public {
        module.initializeWallet(safe1, 1 ether, 5 ether);

        module.pause(safe1);
        assertTrue(module.getPolicy(safe1).paused);

        module.unpause(safe1);
        assertFalse(module.getPolicy(safe1).paused);

        // Should work after unpause
        module.checkTransaction(safe1, merchant1, 0.5 ether, "");
    }

    // ============ Admin: Transfer Sardis ============

    function testTransferSardis() public {
        address newSardis = address(0x7777);
        module.transferSardis(newSardis);
        assertEq(module.sardis(), newSardis);
    }

    function testTransferSardisRevertsZeroAddress() public {
        vm.expectRevert("Invalid address");
        module.transferSardis(address(0));
    }

    function testTransferSardisRevertsIfNotSardis() public {
        vm.prank(notSardis);
        vm.expectRevert("Only Sardis");
        module.transferSardis(address(0x7777));
    }

    function testOldSardisLosesAccess() public {
        address newSardis = address(0x7777);
        module.transferSardis(newSardis);

        // Old sardis (this contract) should no longer be able to act
        vm.expectRevert("Only Sardis");
        module.initializeWallet(safe1, LIMIT_PER_TX, DAILY_LIMIT);
    }

    // ============ Fuzz Tests ============

    function testFuzzCheckTransactionPerTxLimit(uint256 limit, uint256 amount) public {
        limit = bound(limit, 1, type(uint128).max);
        amount = bound(amount, 1, type(uint128).max);
        uint256 daily = limit * 10;

        module.initializeWallet(safe1, limit, daily);

        if (amount <= limit) {
            module.checkTransaction(safe1, merchant1, amount, "");
        } else {
            vm.expectRevert("Exceeds per-tx limit");
            module.checkTransaction(safe1, merchant1, amount, "");
        }
    }

    function testFuzzDailyLimitAccumulation(uint8 numTxs) public {
        uint256 perTx = 1 ether;
        uint256 daily = 5 ether;
        module.initializeWallet(safe1, perTx, daily);

        uint256 totalSpent = 0;
        for (uint8 i = 0; i < numTxs && i < 10; i++) {
            if (totalSpent + perTx <= daily) {
                module.checkTransaction(safe1, merchant1, perTx, "");
                totalSpent += perTx;
            } else {
                vm.expectRevert("Exceeds daily limit");
                module.checkTransaction(safe1, merchant1, perTx, "");
                break;
            }
        }

        assertEq(module.spentToday(safe1), totalSpent);
    }
}
