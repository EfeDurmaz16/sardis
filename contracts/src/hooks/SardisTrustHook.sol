// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../interfaces/IJobHook.sol";
import "../interfaces/IJobRegistry.sol";

/**
 * @title SardisTrustHook
 * @notice Job hook that gates lifecycle transitions on trust scores and job counts
 * @dev Uses IJobRegistry to check:
 *      - beforeFund: client must have trust score >= minClientTrustScore
 *      - beforeSubmit: provider must have completed >= minProviderCompletedJobs
 *      - beforeEvaluate: evaluator must have trust score >= minEvaluatorTrustScore
 *      - after*: no-op
 *
 *      Thresholds are configurable by the contract owner.
 */
contract SardisTrustHook is IJobHook {
    // ============ State Variables ============

    /// @notice Reference to the job registry for trust scores
    IJobRegistry public immutable registry;

    /// @notice Contract owner (can configure thresholds)
    address public owner;

    /// @notice Minimum trust score (basis points) for clients to fund jobs
    uint256 public minClientTrustScore;

    /// @notice Minimum completed jobs for providers to submit work
    uint256 public minProviderCompletedJobs;

    /// @notice Minimum trust score (basis points) for evaluators
    uint256 public minEvaluatorTrustScore;

    // ============ Events ============

    event ThresholdsUpdated(uint256 minClientTrust, uint256 minProviderJobs, uint256 minEvaluatorTrust);
    event OwnerTransferred(address indexed oldOwner, address indexed newOwner);

    // ============ Errors ============

    error NotOwner();
    error ZeroAddress();
    error InvalidThreshold();

    // ============ Constructor ============

    /**
     * @param _registry Address of the IJobRegistry contract
     * @param _owner Address that can configure thresholds
     * @param _minClientTrustScore Initial minimum client trust score (basis points, max 10000)
     * @param _minProviderCompletedJobs Initial minimum provider completed jobs
     * @param _minEvaluatorTrustScore Initial minimum evaluator trust score (basis points, max 10000)
     */
    constructor(
        address _registry,
        address _owner,
        uint256 _minClientTrustScore,
        uint256 _minProviderCompletedJobs,
        uint256 _minEvaluatorTrustScore
    ) {
        if (_registry == address(0) || _owner == address(0)) revert ZeroAddress();
        if (_minClientTrustScore > 10000 || _minEvaluatorTrustScore > 10000) revert InvalidThreshold();

        registry = IJobRegistry(_registry);
        owner = _owner;
        minClientTrustScore = _minClientTrustScore;
        minProviderCompletedJobs = _minProviderCompletedJobs;
        minEvaluatorTrustScore = _minEvaluatorTrustScore;
    }

    // ============ IJobHook Implementation ============

    /// @inheritdoc IJobHook
    function beforeFund(uint256, address client) external view override returns (bool) {
        uint256 score = registry.getTrustScore(client);
        return score >= minClientTrustScore;
    }

    /// @inheritdoc IJobHook
    function afterFund(uint256, address) external override {
        // no-op
    }

    /// @inheritdoc IJobHook
    function beforeSubmit(uint256, address provider) external view override returns (bool) {
        IJobRegistry.AgentReputation memory rep = registry.getReputation(provider);
        return rep.completedJobs >= minProviderCompletedJobs;
    }

    /// @inheritdoc IJobHook
    function afterSubmit(uint256, address) external override {
        // no-op
    }

    /// @inheritdoc IJobHook
    function beforeEvaluate(uint256, address evaluator, bool) external view override returns (bool) {
        uint256 score = registry.getTrustScore(evaluator);
        return score >= minEvaluatorTrustScore;
    }

    /// @inheritdoc IJobHook
    function afterEvaluate(uint256, address, bool) external override {
        // no-op
    }

    // ============ Admin Functions ============

    /**
     * @notice Update trust thresholds
     * @param _minClientTrustScore New minimum client trust score (basis points)
     * @param _minProviderCompletedJobs New minimum provider completed jobs
     * @param _minEvaluatorTrustScore New minimum evaluator trust score (basis points)
     */
    function setThresholds(
        uint256 _minClientTrustScore,
        uint256 _minProviderCompletedJobs,
        uint256 _minEvaluatorTrustScore
    ) external {
        if (msg.sender != owner) revert NotOwner();
        if (_minClientTrustScore > 10000 || _minEvaluatorTrustScore > 10000) revert InvalidThreshold();

        minClientTrustScore = _minClientTrustScore;
        minProviderCompletedJobs = _minProviderCompletedJobs;
        minEvaluatorTrustScore = _minEvaluatorTrustScore;

        emit ThresholdsUpdated(_minClientTrustScore, _minProviderCompletedJobs, _minEvaluatorTrustScore);
    }

    /**
     * @notice Transfer ownership
     * @param newOwner New owner address
     */
    function transferOwnership(address newOwner) external {
        if (msg.sender != owner) revert NotOwner();
        if (newOwner == address(0)) revert ZeroAddress();
        address oldOwner = owner;
        owner = newOwner;
        emit OwnerTransferred(oldOwner, newOwner);
    }
}
