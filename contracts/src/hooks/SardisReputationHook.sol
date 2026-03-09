// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../interfaces/IJobHook.sol";
import "../interfaces/IJob.sol";
import "../SardisJobRegistry.sol";

/**
 * @title SardisReputationHook
 * @notice Job hook that writes reputation data to SardisJobRegistry on lifecycle events
 * @dev Integrates with SardisJobManager to automatically update agent reputation:
 *      - afterFund: recordSpending for the client
 *      - afterEvaluate(approved=true): recordCompletion for the provider
 *      - afterEvaluate(approved=false): recordRejection for the provider
 *      - before*: always returns true (permissive)
 *
 *      This hook must be registered as an authorizedWriter on the SardisJobRegistry.
 *      It also needs a reference to the job manager to look up job details for amounts.
 */
contract SardisReputationHook is IJobHook {
    // ============ State Variables ============

    /// @notice The reputation registry this hook writes to
    SardisJobRegistry public immutable registry;

    /// @notice The job manager contract (for reading job details)
    IJob public immutable jobManager;

    // ============ Errors ============

    error ZeroAddress();

    // ============ Constructor ============

    /**
     * @param _registry Address of the SardisJobRegistry
     * @param _jobManager Address of the SardisJobManager (IJob)
     */
    constructor(address _registry, address _jobManager) {
        if (_registry == address(0) || _jobManager == address(0)) revert ZeroAddress();
        registry = SardisJobRegistry(_registry);
        jobManager = IJob(_jobManager);
    }

    // ============ IJobHook Implementation ============

    /// @inheritdoc IJobHook
    function beforeFund(uint256, address) external pure override returns (bool) {
        return true;
    }

    /// @inheritdoc IJobHook
    function afterFund(uint256 jobId, address client) external override {
        IJob.Job memory job = jobManager.getJob(jobId);
        registry.recordSpending(client, job.amount);
    }

    /// @inheritdoc IJobHook
    function beforeSubmit(uint256, address) external pure override returns (bool) {
        return true;
    }

    /// @inheritdoc IJobHook
    function afterSubmit(uint256, address) external override {
        // no-op
    }

    /// @inheritdoc IJobHook
    function beforeEvaluate(uint256, address, bool) external pure override returns (bool) {
        return true;
    }

    /// @inheritdoc IJobHook
    function afterEvaluate(uint256 jobId, address, bool approved) external override {
        IJob.Job memory job = jobManager.getJob(jobId);
        if (approved) {
            registry.recordCompletion(job.provider, job.amount);
        } else {
            registry.recordRejection(job.provider);
        }
    }
}
