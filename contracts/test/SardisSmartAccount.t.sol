// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SardisSmartAccount.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockUSDC4337 is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {}

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract SardisSmartAccountTest is Test {
    SardisSmartAccount internal account;
    MockUSDC4337 internal usdc;

    address internal owner = address(0xABCD);
    address internal policySigner = vm.addr(0xBEEF);
    address internal recipient = address(0xC0FFEE);

    function setUp() public {
        // Use this test contract as mock entrypoint for authorization checks.
        account = new SardisSmartAccount(owner, policySigner, address(this));
        usdc = new MockUSDC4337();
        usdc.mint(address(account), 1_000_000e6);
    }

    function testExecuteTransferFromEntrypoint() public {
        bytes memory transferData = abi.encodeCall(usdc.transfer, (recipient, 100e6));

        account.execute(address(usdc), 0, transferData);

        assertEq(usdc.balanceOf(recipient), 100e6);
    }

    function testExecuteRevertsForUnauthorizedCaller() public {
        bytes memory transferData = abi.encodeCall(usdc.transfer, (recipient, 100e6));
        vm.prank(address(0xDEAD));
        vm.expectRevert();
        account.execute(address(usdc), 0, transferData);
    }

    function testSetPolicySignerOnlyOwner() public {
        address newSigner = vm.addr(0x1234);

        vm.prank(owner);
        account.setPolicySigner(newSigner);

        assertEq(account.policySigner(), newSigner);

        vm.prank(address(0xBAD));
        vm.expectRevert();
        account.setPolicySigner(policySigner);
    }

    function testPauseBlocksExecute() public {
        vm.prank(owner);
        account.pause();

        bytes memory transferData = abi.encodeCall(usdc.transfer, (recipient, 10e6));
        vm.expectRevert();
        account.execute(address(usdc), 0, transferData);
    }
}
