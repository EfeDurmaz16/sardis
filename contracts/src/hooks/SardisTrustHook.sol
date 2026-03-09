// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../interfaces/IACPHook.sol";
import "../interfaces/IJob.sol";
import "../interfaces/IJobRegistry.sol";

/**
 * @title SardisTrustHook
 * @notice ERC-8183 compliant hook that gates lifecycle transitions on trust scores
 * @dev Uses IACPHook selector-based dispatch:
 *      - beforeAction(fund): client must have trust score >= minClientTrustScore
 *      - beforeAction(submit): provider must have completed >= minProviderCompletedJobs
 *      - beforeAction(complete/reject): evaluator must have trust score >= minEvaluatorTrustScore
 *      - afterAction: no-op
 *
 *      Reverts in beforeAction block the transition.
 */
contract SardisTrustHook is IACPHook {
    /// @notice Reference to the job registry for trust scores
    IJobRegistry public immutable registry;

    /// @notice The job manager contract (for reading job details)
    IJob public immutable jobManager;

    /// @notice Contract owner (can configure thresholds)
    address public owner;

    /// @notice Minimum trust score (basis points) for clients to fund jobs
    uint256 public minClientTrustScore;

    /// @notice Minimum completed jobs for providers to submit work
    uint256 public minProviderCompletedJobs;

    /// @notice Minimum trust score (basis points) for evaluators
    uint256 public minEvaluatorTrustScore;

    event ThresholdsUpdated(uint256 minClientTrust, uint256 minProviderJobs, uint256 minEvaluatorTrust);
    event OwnerTransferred(address indexed oldOwner, address indexed newOwner);

    error NotOwner();
    error ZeroAddress();
    error InvalidThreshold();
    error InsufficientTrustScore(address account, uint256 score, uint256 required);
    error InsufficientCompletedJobs(address provider, uint256 completed, uint256 required);

    constructor(
        address _registry,
        address _jobManager,
        address _owner,
        uint256 _minClientTrustScore,
        uint256 _minProviderCompletedJobs,
        uint256 _minEvaluatorTrustScore
    ) {
        if (_registry == address(0) || _jobManager == address(0) || _owner == address(0)) {
            revert ZeroAddress();
        }
        if (_minClientTrustScore > 10000 || _minEvaluatorTrustScore > 10000) revert InvalidThreshold();

        registry = IJobRegistry(_registry);
        jobManager = IJob(_jobManager);
        owner = _owner;
        minClientTrustScore = _minClientTrustScore;
        minProviderCompletedJobs = _minProviderCompletedJobs;
        minEvaluatorTrustScore = _minEvaluatorTrustScore;
    }

    /// @inheritdoc IACPHook
    function beforeAction(uint256 jobId, bytes4 selector, bytes calldata) external view override {
        IJob.Job memory job = jobManager.getJob(jobId);

        if (selector == IJob.fund.selector) {
            uint256 score = registry.getTrustScore(job.client);
            if (score < minClientTrustScore) {
                revert InsufficientTrustScore(job.client, score, minClientTrustScore);
            }
        } else if (selector == IJob.submit.selector) {
            IJobRegistry.AgentReputation memory rep = registry.getReputation(job.provider);
            if (rep.completedJobs < minProviderCompletedJobs) {
                revert InsufficientCompletedJobs(job.provider, rep.completedJobs, minProviderCompletedJobs);
            }
        } else if (selector == IJob.complete.selector || selector == IJob.reject.selector) {
            uint256 score = registry.getTrustScore(job.evaluator);
            if (score < minEvaluatorTrustScore) {
                revert InsufficientTrustScore(job.evaluator, score, minEvaluatorTrustScore);
            }
        }
    }

    /// @inheritdoc IACPHook
    function afterAction(uint256, bytes4, bytes calldata) external pure override {
        // no-op
    }

    // ============ Admin Functions ============

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

    function transferOwnership(address newOwner) external {
        if (msg.sender != owner) revert NotOwner();
        if (newOwner == address(0)) revert ZeroAddress();
        address oldOwner = owner;
        owner = newOwner;
        emit OwnerTransferred(oldOwner, newOwner);
    }
}
