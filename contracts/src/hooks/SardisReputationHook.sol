// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../interfaces/IACPHook.sol";
import "../interfaces/IJob.sol";
import "../SardisJobRegistry.sol";

/**
 * @title SardisReputationHook
 * @notice ERC-8183 compliant hook that writes reputation data on lifecycle events
 * @dev Uses IACPHook selector-based dispatch:
 *      - afterAction(fund): recordSpending for the client
 *      - afterAction(complete): recordCompletion for the provider
 *      - afterAction(reject): recordRejection for the provider (if was submitted)
 *      - beforeAction: always passes (no revert)
 *
 *      This hook must be registered as an authorizedWriter on the SardisJobRegistry.
 */
contract SardisReputationHook is IACPHook {
    /// @notice The reputation registry this hook writes to
    SardisJobRegistry public immutable registry;

    /// @notice The job manager contract (for reading job details)
    IJob public immutable jobManager;

    error ZeroAddress();

    constructor(address _registry, address _jobManager) {
        if (_registry == address(0) || _jobManager == address(0)) revert ZeroAddress();
        registry = SardisJobRegistry(_registry);
        jobManager = IJob(_jobManager);
    }

    /// @inheritdoc IACPHook
    function beforeAction(uint256, bytes4, bytes calldata) external pure override {
        // Permissive: never blocks
    }

    /// @inheritdoc IACPHook
    function afterAction(uint256 jobId, bytes4 selector, bytes calldata) external override {
        IJob.Job memory job = jobManager.getJob(jobId);

        if (selector == IJob.fund.selector) {
            // Client funded a job — record spending
            registry.recordSpending(job.client, job.budget);
        } else if (selector == IJob.complete.selector) {
            // Evaluator approved — record completion for provider
            registry.recordCompletion(job.provider, job.budget);
        } else if (selector == IJob.reject.selector) {
            // Evaluator rejected — record rejection for provider
            // Only counts if job was submitted (provider did work)
            if (job.status == IJob.JobStatus.Rejected) {
                registry.recordRejection(job.provider);
            }
        }
    }
}
