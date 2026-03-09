// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IJobHook
 * @notice Hook interface for ERC-8183 job lifecycle extensibility
 * @dev Hooks are called at each lifecycle transition. `before*` hooks can gate
 *      execution by returning false. `after*` hooks are fire-and-forget.
 *
 *      Gas budget: Hooks receive a limited gas stipend (HOOK_GAS_LIMIT).
 *      If a hook reverts or runs out of gas, the job manager FAILS OPEN
 *      (continues execution). If a before-hook explicitly returns false,
 *      the job manager reverts the transaction.
 */
interface IJobHook {
    /**
     * @notice Called before a job is funded
     * @param jobId The job being funded
     * @param client The address funding the job
     * @return proceed True to allow funding, false to block
     */
    function beforeFund(uint256 jobId, address client) external returns (bool proceed);

    /**
     * @notice Called after a job is funded
     * @param jobId The funded job
     * @param client The address that funded the job
     */
    function afterFund(uint256 jobId, address client) external;

    /**
     * @notice Called before a deliverable is submitted
     * @param jobId The job being submitted
     * @param provider The address submitting work
     * @return proceed True to allow submission, false to block
     */
    function beforeSubmit(uint256 jobId, address provider) external returns (bool proceed);

    /**
     * @notice Called after a deliverable is submitted
     * @param jobId The submitted job
     * @param provider The address that submitted work
     */
    function afterSubmit(uint256 jobId, address provider) external;

    /**
     * @notice Called before a job is evaluated
     * @param jobId The job being evaluated
     * @param evaluator The address evaluating the job
     * @param approved Whether the evaluator is approving or rejecting
     * @return proceed True to allow evaluation, false to block
     */
    function beforeEvaluate(uint256 jobId, address evaluator, bool approved) external returns (bool proceed);

    /**
     * @notice Called after a job is evaluated
     * @param jobId The evaluated job
     * @param evaluator The address that evaluated the job
     * @param approved Whether the job was approved or rejected
     */
    function afterEvaluate(uint256 jobId, address evaluator, bool approved) external;
}
