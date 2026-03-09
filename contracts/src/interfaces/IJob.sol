// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IJob
 * @notice ERC-8183 Job primitive for agent-to-agent commerce
 * @dev Defines the core lifecycle for jobs between Client, Provider, and Evaluator parties.
 *      Jobs follow the state machine: Open → Funded → Submitted → Completed|Rejected
 *      with alternative terminal states: Expired, Cancelled.
 */
interface IJob {
    // ============ Enums ============

    enum JobStatus {
        Open,
        Funded,
        Submitted,
        Completed,
        Rejected,
        Expired,
        Cancelled
    }

    // ============ Structs ============

    struct Job {
        address client;
        address provider;
        address evaluator;
        address token;
        uint256 amount;
        uint256 deadline;
        bytes32 jobHash;
        address hook;
        JobStatus status;
    }

    // ============ Events ============

    event JobCreated(
        uint256 indexed jobId,
        address indexed client,
        address indexed provider,
        address evaluator,
        address token,
        uint256 amount,
        uint256 deadline,
        bytes32 jobHash,
        address hook
    );

    event JobFunded(uint256 indexed jobId, address indexed client, uint256 amount, uint256 fee);

    event JobSubmitted(uint256 indexed jobId, address indexed provider, bytes32 deliverableHash);

    event JobEvaluated(uint256 indexed jobId, address indexed evaluator, bool approved);

    event JobExpired(uint256 indexed jobId, address indexed client, uint256 refundAmount);

    event JobCancelled(uint256 indexed jobId, address indexed client);

    // ============ Functions ============

    /**
     * @notice Create a new job with specified parameters
     * @param provider Address that will deliver work
     * @param evaluator Address that will evaluate the deliverable
     * @param token ERC-20 token used for payment
     * @param amount Payment amount for the job
     * @param deadline Unix timestamp after which the job can be expired
     * @param jobHash Content-addressable hash of the job specification
     * @param hook Optional hook contract for lifecycle callbacks (address(0) for none)
     * @return jobId The unique identifier for the created job
     */
    function createJob(
        address provider,
        address evaluator,
        address token,
        uint256 amount,
        uint256 deadline,
        bytes32 jobHash,
        address hook
    ) external returns (uint256 jobId);

    /**
     * @notice Fund a job by transferring tokens into escrow
     * @param jobId The job to fund
     */
    function fundJob(uint256 jobId) external;

    /**
     * @notice Submit a deliverable for evaluation
     * @param jobId The job being delivered
     * @param deliverableHash Content-addressable hash of the deliverable
     */
    function submitJob(uint256 jobId, bytes32 deliverableHash) external;

    /**
     * @notice Evaluate a submitted deliverable
     * @param jobId The job to evaluate
     * @param approved True to complete (pay provider), false to reject (refund client)
     */
    function evaluateJob(uint256 jobId, bool approved) external;

    /**
     * @notice Expire a job past its deadline, refunding the client
     * @param jobId The job to expire
     */
    function expireJob(uint256 jobId) external;

    /**
     * @notice Cancel an unfunded job
     * @param jobId The job to cancel
     */
    function cancelJob(uint256 jobId) external;

    /**
     * @notice Get job details
     * @param jobId The job identifier
     * @return job The full job struct
     */
    function getJob(uint256 jobId) external view returns (Job memory job);
}
