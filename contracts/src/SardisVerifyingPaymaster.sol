// SPDX-License-Identifier: MIT
// DEPRECATED: This contract has been superseded by Circle Paymaster (permissionless, no deployment needed).
// Circle Paymaster address (all chains): 0x0578cFB241215b77442a541325d6A4E6dFE700Ec
// Kept for reference only — do NOT deploy to mainnet.
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/interfaces/draft-IERC4337.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/account/utils/draft-ERC4337Utils.sol";

/**
 * @title SardisVerifyingPaymaster
 * @notice ERC-4337 paymaster with wallet allowlist and sponsor caps.
 * @dev Validation supports optional off-chain verifier signatures in paymasterData.
 */
contract SardisVerifyingPaymaster is IPaymaster, Ownable, Pausable {
    using ECDSA for bytes32;

    IEntryPoint public immutable entryPoint;

    /// @notice Optional verifier signer for sponsorship approvals.
    address public verifier;

    /// @notice Max cost allowed per sponsored operation.
    uint256 public maxSponsoredCostPerOp;

    /// @notice Daily sponsorship cap for this paymaster.
    uint256 public dailySponsorCap;

    /// @notice Amount spent today in wei-equivalent units.
    uint256 public spentToday;

    /// @notice Last day index for daily cap accounting.
    uint256 public lastSpendDay;

    mapping(address => bool) public allowedWallets;
    mapping(address => bool) public allowedTokens;

    event WalletAllowlistUpdated(address indexed wallet, bool allowed);
    event TokenAllowlistUpdated(address indexed token, bool allowed);
    event SponsorshipCapsUpdated(uint256 maxPerOp, uint256 dailyCap);
    event VerifierUpdated(address indexed oldVerifier, address indexed newVerifier);

    error NotEntryPoint();
    error WalletNotAllowed(address wallet);
    error CostLimitExceeded(uint256 maxCost, uint256 limit);
    error DailyCapExceeded(uint256 maxCost, uint256 remaining);
    error InvalidVerifierSignature();

    constructor(
        address entryPoint_,
        address owner_,
        uint256 maxSponsoredCostPerOp_,
        uint256 dailySponsorCap_
    ) Ownable(owner_) {
        require(entryPoint_ != address(0), "entrypoint=0");
        entryPoint = IEntryPoint(entryPoint_);
        maxSponsoredCostPerOp = maxSponsoredCostPerOp_;
        dailySponsorCap = dailySponsorCap_;
        lastSpendDay = block.timestamp / 1 days;
    }

    modifier onlyEntryPoint() {
        if (msg.sender != address(entryPoint)) revert NotEntryPoint();
        _;
    }

    function setWalletAllowed(address wallet, bool allowed) external onlyOwner {
        allowedWallets[wallet] = allowed;
        emit WalletAllowlistUpdated(wallet, allowed);
    }

    function setTokenAllowed(address token, bool allowed) external onlyOwner {
        allowedTokens[token] = allowed;
        emit TokenAllowlistUpdated(token, allowed);
    }

    function setCaps(uint256 maxPerOp, uint256 dailyCap) external onlyOwner {
        maxSponsoredCostPerOp = maxPerOp;
        dailySponsorCap = dailyCap;
        emit SponsorshipCapsUpdated(maxPerOp, dailyCap);
    }

    function setVerifier(address newVerifier) external onlyOwner {
        address old = verifier;
        verifier = newVerifier;
        emit VerifierUpdated(old, newVerifier);
    }

    function withdrawTo(address payable to, uint256 amount) external onlyOwner {
        entryPoint.withdrawTo(to, amount);
    }

    function deposit() external payable {
        entryPoint.depositTo{value: msg.value}(address(this));
    }

    /**
     * @inheritdoc IPaymaster
     */
    function validatePaymasterUserOp(
        PackedUserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost
    ) external override onlyEntryPoint whenNotPaused returns (bytes memory context, uint256 validationData) {
        if (!allowedWallets[userOp.sender]) revert WalletNotAllowed(userOp.sender);
        if (maxCost > maxSponsoredCostPerOp) revert CostLimitExceeded(maxCost, maxSponsoredCostPerOp);

        _rollDayIfNeeded();
        uint256 remaining = dailySponsorCap > spentToday ? (dailySponsorCap - spentToday) : 0;
        if (maxCost > remaining) revert DailyCapExceeded(maxCost, remaining);

        // Optional paymasterData format: abi.encode(address token, bytes verifierSignature)
        if (userOp.paymasterAndData.length >= 52 + 32 + 32) {
            bytes calldata paymasterData = ERC4337Utils.paymasterData(userOp);
            (address token, bytes memory sig) = abi.decode(paymasterData, (address, bytes));
            if (token != address(0)) {
                require(allowedTokens[token], "token_not_allowed");
            }
            if (verifier != address(0)) {
                bytes32 innerHash = keccak256(
                    abi.encodePacked(address(this), block.chainid, userOp.sender, token, maxCost, userOpHash)
                );
                bytes32 digest = keccak256(abi.encodePacked("\\x19Ethereum Signed Message:\\n32", innerHash));
                if (digest.recover(sig) != verifier) revert InvalidVerifierSignature();
            }
        }

        context = abi.encode(userOp.sender, maxCost);
        validationData = ERC4337Utils.SIG_VALIDATION_SUCCESS;
    }

    /**
     * @inheritdoc IPaymaster
     */
    function postOp(
        PostOpMode,
        bytes calldata context,
        uint256 actualGasCost,
        uint256
    ) external override onlyEntryPoint {
        (address sender, uint256 reservedMaxCost) = abi.decode(context, (address, uint256));
        sender; // silence unused var warning while preserving context shape
        reservedMaxCost;

        _rollDayIfNeeded();
        spentToday += actualGasCost;
    }

    function _rollDayIfNeeded() internal {
        uint256 today = block.timestamp / 1 days;
        if (today != lastSpendDay) {
            lastSpendDay = today;
            spentToday = 0;
        }
    }
}
