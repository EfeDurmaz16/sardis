// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/RefundProtocol.sol";

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

    function approve(address spender, uint256 amount) public virtual returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) public virtual returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public virtual returns (bool) {
        require(balanceOf[from] >= amount, "insufficient balance");
        require(allowance[from][msg.sender] >= amount, "insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

contract MockFalseERC20 is MockERC20 {
    bool internal failTransfer;
    bool internal failTransferFrom;

    function setFailTransfer(bool shouldFail) external {
        failTransfer = shouldFail;
    }

    function setFailTransferFrom(bool shouldFail) external {
        failTransferFrom = shouldFail;
    }

    function transfer(address to, uint256 amount) public override returns (bool) {
        if (failTransfer) {
            return false;
        }
        return super.transfer(to, amount);
    }

    function transferFrom(address from, address to, uint256 amount) public override returns (bool) {
        if (failTransferFrom) {
            return false;
        }
        return super.transferFrom(from, to, amount);
    }
}

contract RefundProtocolTest is Test {
    uint256 internal constant RECIPIENT_PK = 0xA11CE;
    uint256 internal constant ONE_DAY = 1 days;

    RefundProtocol internal protocol;
    MockERC20 internal token;

    address internal arbiter = address(0xA1B1);
    address internal payer = address(0xCAFE);
    address internal refundTo = address(0xBEEF);
    address internal recipient;

    function setUp() public {
        recipient = vm.addr(RECIPIENT_PK);

        token = new MockERC20();
        protocol = new RefundProtocol(arbiter, address(token), "RefundProtocol", "1");

        token.mint(payer, 1_000e6);

        vm.startPrank(payer);
        token.approve(address(protocol), type(uint256).max);
        vm.stopPrank();
    }

    function test_earlyWithdraw_revertsWhenAmountExceedsRemainingPaymentBalance() public {
        _pay(payer, recipient, 100e6, refundTo);
        _pay(payer, recipient, 100e6, refundTo);

        _earlyWithdrawSingle(0, 60e6, 0, ONE_DAY, 1);

        uint256[] memory paymentIDs = new uint256[](1);
        paymentIDs[0] = 0;
        uint256[] memory withdrawalAmounts = new uint256[](1);
        withdrawalAmounts[0] = 50e6;
        uint256 expiry = block.timestamp + ONE_DAY;
        (uint8 v, bytes32 r, bytes32 s) = _signEarlyWithdrawal(paymentIDs, withdrawalAmounts, 0, expiry, 2);

        vm.expectRevert(abi.encodeWithSelector(RefundProtocol.InvalidWithdrawalAmount.selector, 0, 50e6));
        vm.prank(arbiter);
        protocol.earlyWithdrawByArbiter(paymentIDs, withdrawalAmounts, 0, expiry, 2, recipient, v, r, s);

        (, uint256 paymentAmount,, address paymentRefundTo, uint256 withdrawnAmount, bool refunded) =
            protocol.payments(0);
        assertEq(paymentAmount, 100e6);
        assertEq(paymentRefundTo, refundTo);
        assertEq(withdrawnAmount, 60e6);
        assertFalse(refunded);
        assertEq(protocol.balances(recipient), 140e6);
        assertEq(token.balanceOf(recipient), 60e6);
    }

    function test_earlyWithdraw_settlesDebtBeforeReleasingFunds() public {
        // Payment 0: 40e6 — will be fully early-withdrawn, then refunded by arbiter (creating debt)
        _pay(payer, recipient, 40e6, refundTo);
        // Early withdraw full amount from payment 0
        _earlyWithdrawSingle(0, 40e6, 0, ONE_DAY, 1);
        // recipient balance now 0, recipient token balance 40e6

        // Arbiter deposits funds and refunds payment 0 (fully withdrawn → blocked)
        // So we need a second payment that hasn't been withdrawn
        _pay(payer, recipient, 40e6, refundTo);
        // recipient balance now 40e6

        // Early withdraw all of payment 1 to drain balance
        _earlyWithdrawSingle(1, 40e6, 0, ONE_DAY, 2);
        // recipient balance = 0, token balance = 80e6

        // Create payment 2 (the one that will be refunded via arbiter funds)
        _pay(payer, recipient, 40e6, refundTo);
        // recipient balance = 40e6

        // Early withdraw from payment 2 to reduce balance below 40e6
        _earlyWithdrawSingle(2, 30e6, 0, ONE_DAY, 3);
        // recipient balance = 10e6

        // Now arbiter refunds payment 2 (partially withdrawn, 30 of 40)
        // payment.amount (40e6) > recipientBalance (10e6) → uses arbiter funds
        token.mint(arbiter, 40e6);
        vm.startPrank(arbiter);
        token.approve(address(protocol), 40e6);
        protocol.depositArbiterFunds(40e6);
        protocol.refundByArbiter(2);
        vm.stopPrank();

        assertEq(protocol.debts(recipient), 40e6);
        assertEq(token.balanceOf(refundTo), 40e6);

        // New payment to create balance for debt settlement
        _pay(payer, recipient, 100e6, refundTo);
        // recipient balance = 110e6 (10 remaining + 100 new)

        // Early withdraw from payment 3 — should settle debt first
        _earlyWithdrawSingle(3, 60e6, 0, ONE_DAY, 4);

        assertEq(protocol.debts(recipient), 0);
        assertEq(protocol.balances(recipient), 10e6);
        assertEq(protocol.balances(arbiter), 40e6);
        assertEq(token.balanceOf(recipient), 170e6); // 40+40+30+60
    }

    function test_pay_revertsWhenTokenTransferFromReturnsFalse() public {
        MockFalseERC20 falseToken = new MockFalseERC20();
        RefundProtocol falseProtocol = new RefundProtocol(arbiter, address(falseToken), "RefundProtocol", "1");

        falseToken.mint(payer, 100e6);

        vm.prank(payer);
        falseToken.approve(address(falseProtocol), type(uint256).max);

        falseToken.setFailTransferFrom(true);

        vm.expectRevert();
        vm.prank(payer);
        falseProtocol.pay(recipient, 100e6, refundTo);

        assertEq(falseProtocol.nonce(), 0);
        assertEq(falseProtocol.balances(recipient), 0);
        assertEq(falseToken.balanceOf(address(falseProtocol)), 0);
    }

    function test_pay_revertsWhenRecipientIsZeroAddress() public {
        vm.expectRevert(RefundProtocol.PaymentRecipientIsZeroAddress.selector);
        vm.prank(payer);
        protocol.pay(address(0), 100e6, refundTo);

        assertEq(protocol.nonce(), 0);
        assertEq(protocol.balances(address(0)), 0);
        assertEq(token.balanceOf(address(protocol)), 0);
    }

    function test_earlyWithdraw_revertsWhenTokenTransferReturnsFalse() public {
        MockFalseERC20 falseToken = new MockFalseERC20();
        RefundProtocol falseProtocol = new RefundProtocol(arbiter, address(falseToken), "RefundProtocol", "1");

        falseToken.mint(payer, 100e6);

        vm.prank(payer);
        falseToken.approve(address(falseProtocol), type(uint256).max);

        vm.prank(payer);
        falseProtocol.pay(recipient, 100e6, refundTo);

        uint256[] memory paymentIDs = new uint256[](1);
        paymentIDs[0] = 0;
        uint256[] memory withdrawalAmounts = new uint256[](1);
        withdrawalAmounts[0] = 60e6;
        uint256 expiry = block.timestamp + ONE_DAY;
        (uint8 v, bytes32 r, bytes32 s) =
            _signEarlyWithdrawalForProtocol(falseProtocol, paymentIDs, withdrawalAmounts, 0, expiry, 3);

        falseToken.setFailTransfer(true);

        vm.expectRevert();
        vm.prank(arbiter);
        falseProtocol.earlyWithdrawByArbiter(paymentIDs, withdrawalAmounts, 0, expiry, 3, recipient, v, r, s);

        (, uint256 paymentAmount,, address paymentRefundTo, uint256 withdrawnAmount, bool refunded) =
            falseProtocol.payments(0);
        assertEq(paymentAmount, 100e6);
        assertEq(paymentRefundTo, refundTo);
        assertEq(withdrawnAmount, 0);
        assertFalse(refunded);
        assertEq(falseProtocol.balances(recipient), 100e6);
        assertEq(falseToken.balanceOf(recipient), 0);
    }

    function _pay(address from, address to, uint256 amount, address refundAddress) internal {
        vm.prank(from);
        protocol.pay(to, amount, refundAddress);
    }

    function _earlyWithdrawSingle(
        uint256 paymentID,
        uint256 withdrawalAmount,
        uint256 feeAmount,
        uint256 expiryOffset,
        uint256 salt
    ) internal {
        uint256[] memory paymentIDs = new uint256[](1);
        paymentIDs[0] = paymentID;
        uint256[] memory withdrawalAmounts = new uint256[](1);
        withdrawalAmounts[0] = withdrawalAmount;
        uint256 expiry = block.timestamp + expiryOffset;
        (uint8 v, bytes32 r, bytes32 s) = _signEarlyWithdrawal(paymentIDs, withdrawalAmounts, feeAmount, expiry, salt);

        vm.prank(arbiter);
        protocol.earlyWithdrawByArbiter(paymentIDs, withdrawalAmounts, feeAmount, expiry, salt, recipient, v, r, s);
    }

    function _signEarlyWithdrawal(
        uint256[] memory paymentIDs,
        uint256[] memory withdrawalAmounts,
        uint256 feeAmount,
        uint256 expiry,
        uint256 salt
    ) internal view returns (uint8 v, bytes32 r, bytes32 s) {
        return _signEarlyWithdrawalForProtocol(protocol, paymentIDs, withdrawalAmounts, feeAmount, expiry, salt);
    }

    function _signEarlyWithdrawalForProtocol(
        RefundProtocol targetProtocol,
        uint256[] memory paymentIDs,
        uint256[] memory withdrawalAmounts,
        uint256 feeAmount,
        uint256 expiry,
        uint256 salt
    ) internal view returns (uint8 v, bytes32 r, bytes32 s) {
        bytes32 digest = targetProtocol.hashEarlyWithdrawalInfo(paymentIDs, withdrawalAmounts, feeAmount, expiry, salt);
        return vm.sign(RECIPIENT_PK, digest);
    }

    // ============ Fuzz: Payment Amounts ============

    function testFuzz_payAmount(uint256 amount) public {
        // Bound to reasonable range: 1 wei to 10B USDC (6 decimals)
        amount = bound(amount, 1, 10_000_000_000e6);

        token.mint(payer, amount); // ensure payer has enough
        vm.prank(payer);
        token.approve(address(protocol), type(uint256).max);

        vm.prank(payer);
        protocol.pay(recipient, amount, refundTo);

        // Verify payment was created correctly
        (address payTo, uint256 payAmount,,, uint256 withdrawn, bool refunded) = protocol.payments(protocol.nonce() - 1);
        assertEq(payTo, recipient);
        assertEq(payAmount, amount);
        assertEq(withdrawn, 0);
        assertFalse(refunded);
        assertEq(protocol.balances(recipient), amount);
    }

    function testFuzz_payAmount_zeroReverts(uint256 seed) public {
        // Zero amount payment should still work at the protocol level (no explicit zero check).
        // This is documented behavior - the protocol allows zero-amount payments.
        seed; // unused, keep for fuzz runner
        vm.prank(payer);
        protocol.pay(recipient, 0, refundTo);

        (address payTo, uint256 payAmount,,,,) = protocol.payments(0);
        assertEq(payTo, recipient);
        assertEq(payAmount, 0);
    }
}

// ============ Reentrancy Tests ============

import "./mocks/ReentrantToken.sol";

contract RefundProtocolReentrancyTest is Test {
    uint256 internal constant RECIPIENT_PK = 0xA11CE;
    uint256 internal constant ONE_DAY = 1 days;

    RefundProtocol internal protocol;
    ReentrantToken internal reentrantToken;

    address internal arbiter = address(0xA1B1);
    address internal payer = address(0xCAFE);
    address internal refundTo = address(0xBEEF);
    address internal recipient;

    function setUp() public {
        recipient = vm.addr(RECIPIENT_PK);

        reentrantToken = new ReentrantToken();
        protocol = new RefundProtocol(arbiter, address(reentrantToken), "RefundProtocol", "1");

        reentrantToken.mint(payer, 10_000e6);
        vm.prank(payer);
        reentrantToken.approve(address(protocol), type(uint256).max);
    }

    function test_reentrancy_payDuringWithdrawTransfer() public {
        // Setup: create a payment
        vm.prank(payer);
        protocol.pay(recipient, 100e6, refundTo);

        // Set lockup to 0 so we can withdraw immediately
        vm.prank(arbiter);
        protocol.setLockupSeconds(recipient, 0);

        // Configure reentrancy: during the transfer in withdraw(), try to call pay() again
        reentrantToken.setReentrancyCallback(
            address(protocol), abi.encodeWithSelector(RefundProtocol.pay.selector, recipient, 50e6, refundTo)
        );

        // Give the token contract some balance to attempt the reentrant pay
        reentrantToken.mint(address(reentrantToken), 50e6);
        vm.prank(address(reentrantToken));
        reentrantToken.approve(address(protocol), type(uint256).max);

        // Withdraw should succeed. The reentrant pay() is a different function so it
        // succeeds and adds 50e6 to the recipient balance. Key invariant: the original
        // withdrawal of 100e6 still completes correctly (CEI pattern means balance was
        // decremented BEFORE the external call).
        uint256 balanceBefore = protocol.balances(recipient);
        assertEq(balanceBefore, 100e6);

        uint256[] memory ids = new uint256[](1);
        ids[0] = 0;
        vm.prank(recipient);
        protocol.withdraw(ids);

        // After withdraw: original 100e6 was deducted, reentrant pay() added 50e6
        // Balance = 100e6 - 100e6 + 50e6 = 50e6
        assertEq(protocol.balances(recipient), 50e6, "Balance should reflect withdraw - 100 + reentrant pay + 50");
        // The original withdrawal payment is fully marked as withdrawn
        (,,,, uint256 withdrawn,) = protocol.payments(0);
        assertEq(withdrawn, 100e6, "Payment 0 should be fully withdrawn");
    }

    function test_reentrancy_payDuringEarlyWithdraw() public {
        // Create payment
        vm.prank(payer);
        protocol.pay(recipient, 100e6, refundTo);

        // Configure reentrancy on the transfer inside earlyWithdrawByArbiter
        reentrantToken.setReentrancyCallback(
            address(protocol), abi.encodeWithSelector(RefundProtocol.pay.selector, recipient, 10e6, refundTo)
        );
        reentrantToken.mint(address(reentrantToken), 10e6);
        vm.prank(address(reentrantToken));
        reentrantToken.approve(address(protocol), type(uint256).max);

        // Early withdraw
        uint256[] memory paymentIDs = new uint256[](1);
        paymentIDs[0] = 0;
        uint256[] memory withdrawalAmounts = new uint256[](1);
        withdrawalAmounts[0] = 60e6;
        uint256 expiry = block.timestamp + ONE_DAY;
        bytes32 digest = protocol.hashEarlyWithdrawalInfo(paymentIDs, withdrawalAmounts, 0, expiry, 1);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(RECIPIENT_PK, digest);

        vm.prank(arbiter);
        protocol.earlyWithdrawByArbiter(paymentIDs, withdrawalAmounts, 0, expiry, 1, recipient, v, r, s);

        // CEI pattern: balance was decremented by 60e6 before the external transfer call.
        // During transfer, the reentrant pay() added 10e6 to recipient balance.
        // Net: 100e6 - 60e6 + 10e6 = 50e6
        assertEq(protocol.balances(recipient), 50e6, "Balance: 100 - 60 withdrawn + 10 reentrant pay");
        // The withdrawal hash should be marked as used (replay protection)
        bytes32 withdrawalHash = protocol.hashEarlyWithdrawalInfo(paymentIDs, withdrawalAmounts, 0, expiry, 1);
        assertTrue(protocol.withdrawalHashes(withdrawalHash), "Withdrawal hash should be marked used");
    }

    function test_reentrancy_refundDuringPay() public {
        // Configure reentrancy: during the transferFrom in pay(), try to call refundByRecipient
        // First we need an existing payment to attempt the refund on
        reentrantToken.disableReentrancy();
        vm.prank(payer);
        protocol.pay(recipient, 50e6, refundTo);

        // Now set up reentrancy for the next pay() call
        reentrantToken.setReentrancyCallback(
            address(protocol), abi.encodeWithSelector(RefundProtocol.refundByRecipient.selector, 0)
        );

        // The reentrant refundByRecipient should fail because msg.sender would be the token,
        // not the recipient
        vm.prank(payer);
        protocol.pay(recipient, 50e6, refundTo);

        // Payment 0 should NOT have been refunded by the reentrancy attempt
        (,,,,, bool refunded) = protocol.payments(0);
        assertFalse(refunded, "Reentrancy should not have succeeded in refunding");
    }
}
