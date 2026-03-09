// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IJob
 * @notice ERC-8183 compliant interface for Agentic Commerce
 * @dev Defines the core job lifecycle as specified in EIP-8183:
 *      Open → Funded → Submitted → Completed | Rejected | Expired
 *
 *      Spec: https://eips.ethereum.org/EIPS/eip-8183
 */
interface IJob {
    // ============ Enums ============

    enum JobStatus {
        Open,       // Created, budget may or may not be set
        Funded,     // Budget escrowed, awaiting provider submission
        Submitted,  // Provider delivered, awaiting evaluator decision
        Completed,  // Terminal: evaluator approved, funds released to provider
        Rejected,   // Terminal: evaluator rejected, funds refunded to client
        Expired     // Terminal: deadline passed, funds refunded to client
    }

    // ============ Structs ============

    struct Job {
        address client;
        address provider;
        address evaluator;
        address token;         // ERC-20 payment token
        uint256 budget;        // Payment amount (set via setBudget)
        uint256 expiredAt;     // Unix timestamp after which job can be expired
        string description;    // Human/agent-readable job description
        address hook;          // Optional IACPHook contract (address(0) = none)
        JobStatus status;
    }

    // ============ Events (ERC-8183 required) ============

    event JobCreated(
        uint256 indexed jobId,
        address indexed client,
        address provider,
        address evaluator,
        uint256 expiredAt,
        string description,
        address hook
    );

    event ProviderSet(
        uint256 indexed jobId,
        address indexed provider
    );

    event BudgetSet(
        uint256 indexed jobId,
        uint256 amount,
        address token
    );

    event JobFunded(
        uint256 indexed jobId,
        address indexed client,
        uint256 amount
    );

    event JobSubmitted(
        uint256 indexed jobId,
        address indexed provider,
        bytes32 deliverable
    );

    event JobCompleted(
        uint256 indexed jobId,
        address indexed evaluator,
        bytes32 reason
    );

    event JobRejected(
        uint256 indexed jobId,
        address indexed evaluator,
        bytes32 reason
    );

    event JobExpired(
        uint256 indexed jobId,
        address indexed client,
        uint256 refundAmount
    );

    event PaymentReleased(
        uint256 indexed jobId,
        address indexed provider,
        uint256 amount,
        uint256 fee
    );

    event Refunded(
        uint256 indexed jobId,
        address indexed client,
        uint256 amount
    );

    // ============ Job Lifecycle Functions ============

    /**
     * @notice Create a new job
     * @param provider Address that will deliver work
     * @param evaluator Address that will evaluate the deliverable
     * @param expiredAt Unix timestamp after which the job can be expired
     * @param description Human/agent-readable job specification
     * @param hook Optional hook contract for lifecycle callbacks (address(0) for none)
     * @return jobId The unique identifier for the created job
     */
    function createJob(
        address provider,
        address evaluator,
        uint256 expiredAt,
        string calldata description,
        address hook
    ) external returns (uint256 jobId);

    /**
     * @notice Set or change the provider for a job
     * @param jobId The job to update
     * @param provider New provider address
     * @param optParams Optional hook-specific parameters
     */
    function setProvider(
        uint256 jobId,
        address provider,
        bytes calldata optParams
    ) external;

    /**
     * @notice Set or change the budget and payment token for a job
     * @param jobId The job to update
     * @param amount Payment amount
     * @param optParams Optional hook-specific parameters
     */
    function setBudget(
        uint256 jobId,
        uint256 amount,
        bytes calldata optParams
    ) external;

    /**
     * @notice Fund a job by transferring tokens into escrow
     * @param jobId The job to fund
     * @param expectedBudget Expected budget amount (reverts if mismatched, prevents front-running)
     * @param optParams Optional hook-specific parameters
     */
    function fund(
        uint256 jobId,
        uint256 expectedBudget,
        bytes calldata optParams
    ) external;

    /**
     * @notice Submit a deliverable for evaluation
     * @param jobId The job being delivered
     * @param deliverable Content-addressable hash of the deliverable
     * @param optParams Optional hook-specific parameters
     */
    function submit(
        uint256 jobId,
        bytes32 deliverable,
        bytes calldata optParams
    ) external;

    /**
     * @notice Complete a job (evaluator approves, releases funds to provider)
     * @param jobId The job to complete
     * @param reason Reason/attestation hash for the completion
     * @param optParams Optional hook-specific parameters
     */
    function complete(
        uint256 jobId,
        bytes32 reason,
        bytes calldata optParams
    ) external;

    /**
     * @notice Reject a job (evaluator or client rejects, refunds client)
     * @param jobId The job to reject
     * @param reason Reason hash for the rejection
     * @param optParams Optional hook-specific parameters
     */
    function reject(
        uint256 jobId,
        bytes32 reason,
        bytes calldata optParams
    ) external;

    /**
     * @notice Claim refund for an expired job
     * @param jobId The expired job
     */
    function claimRefund(uint256 jobId) external;

    // ============ View Functions ============

    /**
     * @notice Get job details
     * @param jobId The job identifier
     * @return job The full job struct
     */
    function getJob(uint256 jobId) external view returns (Job memory job);
}
