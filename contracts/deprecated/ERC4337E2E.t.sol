// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "./SardisSmartAccountFactory.sol";
import "./SardisSmartAccount.sol";
import "../src/SardisVerifyingPaymaster.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/interfaces/draft-IERC4337.sol";

contract MockUSDC4337E2E is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {}

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract ERC4337E2ETest is Test {
    SardisSmartAccountFactory internal factory;
    SardisVerifyingPaymaster internal paymaster;
    MockUSDC4337E2E internal usdc;

    address internal walletOwner = address(0x1111);
    address internal policySigner = vm.addr(0xBEEF);
    address internal merchant = address(0x9999);

    function setUp() public {
        factory = new SardisSmartAccountFactory(address(this), address(this));
        paymaster = new SardisVerifyingPaymaster(address(this), address(this), 1 ether, 10 ether);
        usdc = new MockUSDC4337E2E();
    }

    function testSmartAccountExecuteAndPaymasterValidation() public {
        address smartAccountAddr = factory.createAccount(walletOwner, policySigner, keccak256("e2e"));
        SardisSmartAccount smartAccount = SardisSmartAccount(payable(smartAccountAddr));

        usdc.mint(smartAccountAddr, 1_000e6);
        paymaster.setWalletAllowed(smartAccountAddr, true);

        bytes memory transferData = abi.encodeCall(usdc.transfer, (merchant, 25e6));
        smartAccount.execute(address(usdc), 0, transferData);

        assertEq(usdc.balanceOf(merchant), 25e6);

        PackedUserOperation memory op;
        op.sender = smartAccountAddr;
        op.paymasterAndData = "";

        (, uint256 validationData) = paymaster.validatePaymasterUserOp(op, bytes32("userop"), 0.1 ether);
        assertEq(validationData, 0);
    }
}
