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

        (, uint256 paymentAmount,, address paymentRefundTo, uint256 withdrawnAmount, bool refunded) = protocol.payments(0);
        assertEq(paymentAmount, 100e6);
        assertEq(paymentRefundTo, refundTo);
        assertEq(withdrawnAmount, 60e6);
        assertFalse(refunded);
        assertEq(protocol.balances(recipient), 140e6);
        assertEq(token.balanceOf(recipient), 60e6);
    }

    function test_earlyWithdraw_settlesDebtBeforeReleasingFunds() public {
        _pay(payer, recipient, 40e6, refundTo);
        _earlyWithdrawSingle(0, 40e6, 0, ONE_DAY, 1);

        token.mint(arbiter, 40e6);
        vm.startPrank(arbiter);
        token.approve(address(protocol), 40e6);
        protocol.depositArbiterFunds(40e6);
        protocol.refundByArbiter(0);
        vm.stopPrank();

        assertEq(protocol.debts(recipient), 40e6);
        assertEq(token.balanceOf(refundTo), 40e6);

        _pay(payer, recipient, 100e6, refundTo);
        _earlyWithdrawSingle(1, 60e6, 0, ONE_DAY, 2);

        assertEq(protocol.debts(recipient), 0);
        assertEq(protocol.balances(recipient), 0);
        assertEq(protocol.balances(arbiter), 40e6);
        assertEq(token.balanceOf(recipient), 100e6);
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
        (uint8 v, bytes32 r, bytes32 s) = _signEarlyWithdrawalForProtocol(
            falseProtocol, paymentIDs, withdrawalAmounts, 0, expiry, 3
        );

        falseToken.setFailTransfer(true);

        vm.expectRevert();
        vm.prank(arbiter);
        falseProtocol.earlyWithdrawByArbiter(paymentIDs, withdrawalAmounts, 0, expiry, 3, recipient, v, r, s);

        (, uint256 paymentAmount,, address paymentRefundTo, uint256 withdrawnAmount, bool refunded) = falseProtocol.payments(0);
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
        protocol.earlyWithdrawByArbiter(
            paymentIDs,
            withdrawalAmounts,
            feeAmount,
            expiry,
            salt,
            recipient,
            v,
            r,
            s
        );
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
}
