// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SardisWalletFactory.sol";
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

contract SardisWalletFactoryTest is Test {
    SardisWalletFactory factory;
    MockUSDC usdc;
    
    address deployer = address(this);
    address agent1 = address(0x1);
    address agent2 = address(0x2);
    address recoveryAddress = address(0x999);
    
    uint256 defaultLimitPerTx = 1000 * 10**6;  // 1000 USDC
    uint256 defaultDailyLimit = 10000 * 10**6; // 10000 USDC
    
    event WalletCreated(
        address indexed agent,
        address indexed wallet,
        uint256 limitPerTx,
        uint256 dailyLimit
    );
    
    function setUp() public {
        factory = new SardisWalletFactory(
            defaultLimitPerTx,
            defaultDailyLimit,
            recoveryAddress
        );
        usdc = new MockUSDC();
    }
    
    // ============ Constructor Tests ============
    
    function testConstructorSetsDefaults() public view {
        assertEq(factory.defaultLimitPerTx(), defaultLimitPerTx);
        assertEq(factory.defaultDailyLimit(), defaultDailyLimit);
        assertEq(factory.defaultRecoveryAddress(), recoveryAddress);
        assertEq(factory.owner(), deployer);
    }
    
    // ============ Wallet Creation Tests ============
    
    function testCreateWallet() public {
        vm.expectEmit(true, false, false, true);
        emit WalletCreated(agent1, address(0), defaultLimitPerTx, defaultDailyLimit);
        
        address wallet = factory.createWallet(agent1);
        
        assertTrue(wallet != address(0));
        assertTrue(factory.isValidWallet(wallet));
        assertEq(factory.walletToAgent(wallet), agent1);
        assertEq(factory.getTotalWallets(), 1);
    }
    
    function testCreateWalletWithCustomLimits() public {
        uint256 customLimitPerTx = 500 * 10**6;
        uint256 customDailyLimit = 5000 * 10**6;
        
        address wallet = factory.createWalletWithLimits(agent1, customLimitPerTx, customDailyLimit);
        
        SardisAgentWallet agentWallet = SardisAgentWallet(payable(wallet));
        assertEq(agentWallet.limitPerTx(), customLimitPerTx);
        assertEq(agentWallet.dailyLimit(), customDailyLimit);
    }
    
    function testCreateWalletRevertsWithZeroAddress() public {
        vm.expectRevert("Invalid agent address");
        factory.createWallet(address(0));
    }
    
    function testCreateMultipleWalletsForSameAgent() public {
        address wallet1 = factory.createWallet(agent1);
        address wallet2 = factory.createWallet(agent1);
        
        assertTrue(wallet1 != wallet2);
        assertEq(factory.getAgentWalletCount(agent1), 2);
        
        address[] memory wallets = factory.getAgentWallets(agent1);
        assertEq(wallets.length, 2);
        assertEq(wallets[0], wallet1);
        assertEq(wallets[1], wallet2);
    }
    
    // ============ Deterministic Wallet Creation Tests ============
    
    function testCreateWalletDeterministic() public {
        bytes32 salt = keccak256("test_salt");
        
        address predicted = factory.predictWalletAddress(agent1, salt);
        address actual = factory.createWalletDeterministic(agent1, salt);
        
        assertEq(predicted, actual);
        assertTrue(factory.isValidWallet(actual));
    }
    
    function testDeterministicWalletsSameAddressWithSameSalt() public {
        bytes32 salt = keccak256("same_salt");
        
        address predicted1 = factory.predictWalletAddress(agent1, salt);
        address predicted2 = factory.predictWalletAddress(agent1, salt);
        
        assertEq(predicted1, predicted2);
    }
    
    function testDeterministicWalletsDifferentAddressWithDifferentSalt() public {
        bytes32 salt1 = keccak256("salt1");
        bytes32 salt2 = keccak256("salt2");
        
        address predicted1 = factory.predictWalletAddress(agent1, salt1);
        address predicted2 = factory.predictWalletAddress(agent1, salt2);
        
        assertTrue(predicted1 != predicted2);
    }
    
    // ============ Deployment Fee Tests ============
    
    function testDeploymentFeeRequired() public {
        factory.setDeploymentFee(0.01 ether);
        
        vm.expectRevert("Insufficient deployment fee");
        factory.createWallet(agent1);
        
        address wallet = factory.createWallet{value: 0.01 ether}(agent1);
        assertTrue(wallet != address(0));
    }
    
    function testExcessFeeRefunded() public {
        factory.setDeploymentFee(0.01 ether);
        
        uint256 balanceBefore = address(this).balance;
        factory.createWallet{value: 0.02 ether}(agent1);
        uint256 balanceAfter = address(this).balance;
        
        // Should have paid exactly 0.01 ether (refunded 0.01)
        assertEq(balanceBefore - balanceAfter, 0.01 ether);
    }
    
    function testWithdrawFees() public {
        factory.setDeploymentFee(0.01 ether);
        factory.createWallet{value: 0.01 ether}(agent1);
        factory.createWallet{value: 0.01 ether}(agent2);
        
        address recipient = address(0x888);
        uint256 contractBalance = address(factory).balance;
        
        factory.withdrawFees(recipient);
        
        assertEq(address(factory).balance, 0);
        assertEq(recipient.balance, contractBalance);
    }
    
    // ============ Admin Function Tests ============
    
    function testSetDefaultLimits() public {
        uint256 newLimitPerTx = 2000 * 10**6;
        uint256 newDailyLimit = 20000 * 10**6;
        
        factory.setDefaultLimits(newLimitPerTx, newDailyLimit);
        
        assertEq(factory.defaultLimitPerTx(), newLimitPerTx);
        assertEq(factory.defaultDailyLimit(), newDailyLimit);
    }
    
    function testSetDefaultLimitsOnlyOwner() public {
        vm.prank(agent1);
        vm.expectRevert();
        factory.setDefaultLimits(100, 100);
    }
    
    function testSetRecoveryAddress() public {
        address newRecovery = address(0x777);
        factory.setDefaultRecoveryAddress(newRecovery);
        assertEq(factory.defaultRecoveryAddress(), newRecovery);
    }
    
    function testSetRecoveryAddressRevertsWithZero() public {
        vm.expectRevert("Invalid address");
        factory.setDefaultRecoveryAddress(address(0));
    }
    
    // ============ Pause Tests ============
    
    function testPauseStopsWalletCreation() public {
        factory.pause();
        
        vm.expectRevert();
        factory.createWallet(agent1);
    }
    
    function testUnpauseAllowsWalletCreation() public {
        factory.pause();
        factory.unpause();
        
        address wallet = factory.createWallet(agent1);
        assertTrue(wallet != address(0));
    }
    
    // ============ View Function Tests ============
    
    function testVerifyWallet() public {
        address wallet = factory.createWallet(agent1);
        
        assertTrue(factory.verifyWallet(wallet));
        assertFalse(factory.verifyWallet(address(0x123)));
    }
    
    function testGetTotalWallets() public {
        assertEq(factory.getTotalWallets(), 0);
        
        factory.createWallet(agent1);
        assertEq(factory.getTotalWallets(), 1);
        
        factory.createWallet(agent2);
        assertEq(factory.getTotalWallets(), 2);
    }
    
    // Allow receiving ETH for fee refund tests
    receive() external payable {}
}



