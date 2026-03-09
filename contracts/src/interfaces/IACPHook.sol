// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IACPHook
 * @notice ERC-8183 compliant hook interface for Agentic Commerce Protocol
 * @dev Hooks receive callbacks before and after each job lifecycle transition.
 *      The `selector` parameter identifies which core function is being called
 *      (e.g., the function selector for `fund`).
 *
 *      - beforeAction: MAY revert to block the action. If it does not revert,
 *        the action proceeds.
 *      - afterAction: Fire-and-forget. Reverts are ignored by the caller.
 *
 *      Spec: https://eips.ethereum.org/EIPS/eip-8183
 */
interface IACPHook {
    /**
     * @notice Called before a lifecycle action executes
     * @param jobId The job being acted upon
     * @param selector The function selector of the action (e.g., IJob.fund.selector)
     * @param data ABI-encoded parameters specific to the action
     */
    function beforeAction(
        uint256 jobId,
        bytes4 selector,
        bytes calldata data
    ) external;

    /**
     * @notice Called after a lifecycle action completes
     * @param jobId The job that was acted upon
     * @param selector The function selector of the action
     * @param data ABI-encoded parameters specific to the action
     */
    function afterAction(
        uint256 jobId,
        bytes4 selector,
        bytes calldata data
    ) external;
}
