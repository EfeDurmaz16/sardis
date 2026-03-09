// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

import "./interfaces/IJob.sol";
import "./interfaces/IJobHook.sol";

/**
 * @title SardisJobManager
 * @notice ERC-8183 implementation — escrow-based job primitive for agent-to-agent commerce
 * @dev Manages the full job lifecycle: create → fund → submit → evaluate, with
 *      hook extensibility at each transition. Fees are collected on completion
 *      and refunded on rejection/expiry.
 *
 *      Hook dispatch policy:
 *        - before* hooks: called with HOOK_GAS_LIMIT. If hook returns false, revert.
 *          If hook reverts (gas exhaustion or other), FAIL-OPEN (continue).
 *        - after* hooks: fire-and-forget with HOOK_GAS_LIMIT. Reverts are ignored.
 *
 *      Security:
 *        - ReentrancyGuard on all state-mutating external functions
 *        - SafeERC20 for all token operations
 *        - Pausable for emergency stops
 *        - Strict role checks (client/provider/evaluator) per function
 */
contract SardisJobManager is IJob, ReentrancyGuard, Pausable, Ownable {
    using SafeERC20 for IERC20;

    // ============ Constants ============

    /// @notice Gas limit for hook callbacks to prevent griefing
    uint256 public constant HOOK_GAS_LIMIT = 100_000;

    /// @notice Maximum deadline duration from block.timestamp
    uint256 public constant MAX_DEADLINE_SECONDS = 180 days;

    /// @notice Maximum fee in basis points (5%)
    uint256 public constant MAX_FEE_BPS = 500;

    // ============ State Variables ============

    /// @notice Monotonically increasing job counter
    uint256 public jobCounter;

    /// @notice Job storage by ID
    mapping(uint256 => Job) internal _jobs;

    /// @notice Deliverable hashes submitted by providers
    mapping(uint256 => bytes32) public deliverableHashes;

    /// @notice Protocol fee in basis points
    uint256 public feeBps;

    /// @notice Address receiving protocol fees
    address public feeRecipient;

    /// @notice Tokens allowed for job payments
    mapping(address => bool) public allowedTokens;

    // ============ Errors ============

    error ZeroAddress();
    error InvalidParties();
    error TokenNotAllowed();
    error InvalidDeadline();
    error InvalidAmount();
    error JobNotFound();
    error InvalidJobStatus(JobStatus current, JobStatus expected);
    error NotClient();
    error NotProvider();
    error NotEvaluator();
    error DeadlineNotReached();
    error FeeTooHigh();
    error HookDenied();

    // ============ Constructor ============

    /**
     * @param _owner Contract owner (admin)
     * @param _feeRecipient Address receiving protocol fees
     * @param _feeBps Initial fee in basis points (max 500 = 5%)
     */
    constructor(address _owner, address _feeRecipient, uint256 _feeBps) Ownable(_owner) {
        if (_feeRecipient == address(0)) revert ZeroAddress();
        if (_feeBps > MAX_FEE_BPS) revert FeeTooHigh();
        feeRecipient = _feeRecipient;
        feeBps = _feeBps;
    }

    // ============ Job Lifecycle ============

    /// @inheritdoc IJob
    function createJob(
        address provider,
        address evaluator,
        address token,
        uint256 amount,
        uint256 deadline,
        bytes32 jobHash,
        address hook
    ) external override whenNotPaused nonReentrant returns (uint256 jobId) {
        // Validate addresses
        if (provider == address(0) || evaluator == address(0) || token == address(0)) {
            revert ZeroAddress();
        }
        // Client, provider, evaluator must all be distinct
        if (msg.sender == provider || msg.sender == evaluator || provider == evaluator) {
            revert InvalidParties();
        }
        // Token must be on allowlist
        if (!allowedTokens[token]) revert TokenNotAllowed();
        // Deadline must be in the future and within MAX_DEADLINE_SECONDS
        if (deadline <= block.timestamp || deadline > block.timestamp + MAX_DEADLINE_SECONDS) {
            revert InvalidDeadline();
        }
        // Amount must be positive
        if (amount == 0) revert InvalidAmount();

        jobId = jobCounter;
        _jobs[jobId] = Job({
            client: msg.sender,
            provider: provider,
            evaluator: evaluator,
            token: token,
            amount: amount,
            deadline: deadline,
            jobHash: jobHash,
            hook: hook,
            status: JobStatus.Open
        });

        unchecked {
            ++jobCounter;
        }

        emit JobCreated(jobId, msg.sender, provider, evaluator, token, amount, deadline, jobHash, hook);
    }

    /// @inheritdoc IJob
    function fundJob(uint256 jobId) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        if (msg.sender != job.client) revert NotClient();
        if (job.status != JobStatus.Open) {
            revert InvalidJobStatus(job.status, JobStatus.Open);
        }

        // Before-hook: gate on client
        _callBeforeHook(job.hook, abi.encodeCall(IJobHook.beforeFund, (jobId, msg.sender)));

        // Calculate fee
        uint256 fee = (job.amount * feeBps) / 10000;
        uint256 totalDeposit = job.amount + fee;

        // Transfer tokens from client into escrow
        IERC20(job.token).safeTransferFrom(msg.sender, address(this), totalDeposit);

        job.status = JobStatus.Funded;

        emit JobFunded(jobId, msg.sender, job.amount, fee);

        // After-hook: fire and forget
        _callAfterHook(job.hook, abi.encodeCall(IJobHook.afterFund, (jobId, msg.sender)));
    }

    /// @inheritdoc IJob
    function submitJob(uint256 jobId, bytes32 deliverableHash) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        if (msg.sender != job.provider) revert NotProvider();
        if (job.status != JobStatus.Funded) {
            revert InvalidJobStatus(job.status, JobStatus.Funded);
        }

        // Before-hook: gate on provider
        _callBeforeHook(job.hook, abi.encodeCall(IJobHook.beforeSubmit, (jobId, msg.sender)));

        deliverableHashes[jobId] = deliverableHash;
        job.status = JobStatus.Submitted;

        emit JobSubmitted(jobId, msg.sender, deliverableHash);

        // After-hook: fire and forget
        _callAfterHook(job.hook, abi.encodeCall(IJobHook.afterSubmit, (jobId, msg.sender)));
    }

    /// @inheritdoc IJob
    function evaluateJob(uint256 jobId, bool approved) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        if (msg.sender != job.evaluator) revert NotEvaluator();
        if (job.status != JobStatus.Submitted) {
            revert InvalidJobStatus(job.status, JobStatus.Submitted);
        }

        // Before-hook: gate on evaluator
        _callBeforeHook(job.hook, abi.encodeCall(IJobHook.beforeEvaluate, (jobId, msg.sender, approved)));

        uint256 fee = (job.amount * feeBps) / 10000;

        if (approved) {
            job.status = JobStatus.Completed;

            // Pay provider the job amount
            IERC20(job.token).safeTransfer(job.provider, job.amount);
            // Pay fee to feeRecipient
            if (fee > 0) {
                IERC20(job.token).safeTransfer(feeRecipient, fee);
            }
        } else {
            job.status = JobStatus.Rejected;

            // Refund full deposit (amount + fee) to client
            uint256 totalRefund = job.amount + fee;
            IERC20(job.token).safeTransfer(job.client, totalRefund);
        }

        emit JobEvaluated(jobId, msg.sender, approved);

        // After-hook: fire and forget
        _callAfterHook(job.hook, abi.encodeCall(IJobHook.afterEvaluate, (jobId, msg.sender, approved)));
    }

    /// @inheritdoc IJob
    function expireJob(uint256 jobId) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        // Can only expire funded or submitted jobs
        if (job.status != JobStatus.Funded && job.status != JobStatus.Submitted) {
            revert InvalidJobStatus(job.status, JobStatus.Funded);
        }
        if (block.timestamp < job.deadline) revert DeadlineNotReached();

        uint256 fee = (job.amount * feeBps) / 10000;
        uint256 totalRefund = job.amount + fee;

        job.status = JobStatus.Expired;

        // Refund full deposit to client
        IERC20(job.token).safeTransfer(job.client, totalRefund);

        emit JobExpired(jobId, job.client, totalRefund);
    }

    /// @inheritdoc IJob
    function cancelJob(uint256 jobId) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        if (msg.sender != job.client) revert NotClient();
        if (job.status != JobStatus.Open) {
            revert InvalidJobStatus(job.status, JobStatus.Open);
        }

        job.status = JobStatus.Cancelled;

        emit JobCancelled(jobId, msg.sender);
    }

    // ============ View Functions ============

    /// @inheritdoc IJob
    function getJob(uint256 jobId) external view override returns (Job memory) {
        return _jobs[jobId];
    }

    /**
     * @notice Get multiple jobs in a single call
     * @param jobIds Array of job identifiers
     * @return jobs Array of job structs
     */
    function getJobs(uint256[] calldata jobIds) external view returns (Job[] memory jobs) {
        jobs = new Job[](jobIds.length);
        for (uint256 i = 0; i < jobIds.length; ++i) {
            jobs[i] = _jobs[jobIds[i]];
        }
    }

    // ============ Admin Functions ============

    /**
     * @notice Set the protocol fee in basis points
     * @param _feeBps New fee (max 500 = 5%)
     */
    function setFeeBps(uint256 _feeBps) external onlyOwner {
        if (_feeBps > MAX_FEE_BPS) revert FeeTooHigh();
        feeBps = _feeBps;
    }

    /**
     * @notice Set the fee recipient address
     * @param _feeRecipient New fee recipient
     */
    function setFeeRecipient(address _feeRecipient) external onlyOwner {
        if (_feeRecipient == address(0)) revert ZeroAddress();
        feeRecipient = _feeRecipient;
    }

    /**
     * @notice Add or remove a token from the allowlist
     * @param token ERC-20 token address
     * @param allowed Whether the token should be allowed
     */
    function setAllowedToken(address token, bool allowed) external onlyOwner {
        if (token == address(0)) revert ZeroAddress();
        allowedTokens[token] = allowed;
    }

    /**
     * @notice Pause the contract (emergency stop)
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause the contract
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    // ============ Internal Functions ============

    /**
     * @dev Get a job by ID, reverting if jobId >= jobCounter
     */
    function _getJob(uint256 jobId) internal view returns (Job storage) {
        if (jobId >= jobCounter) revert JobNotFound();
        return _jobs[jobId];
    }

    /**
     * @dev Call a before-hook with gas limit. If the hook returns false, revert.
     *      If the hook reverts (gas exhaustion or other error), FAIL-OPEN (continue).
     * @param hook Hook contract address (address(0) means no hook)
     * @param data Encoded function call
     */
    function _callBeforeHook(address hook, bytes memory data) internal {
        if (hook == address(0)) return;

        (bool success, bytes memory returnData) = hook.call{ gas: HOOK_GAS_LIMIT }(data);

        // If the call succeeded, decode the return value and check if hook denied
        if (success && returnData.length >= 32) {
            bool proceed = abi.decode(returnData, (bool));
            if (!proceed) revert HookDenied();
        }
        // If the call reverted (gas exhaustion, revert, etc.), FAIL-OPEN: continue
    }

    /**
     * @dev Call an after-hook with gas limit. Fire-and-forget: reverts are ignored.
     * @param hook Hook contract address (address(0) means no hook)
     * @param data Encoded function call
     */
    function _callAfterHook(address hook, bytes memory data) internal {
        if (hook == address(0)) return;
        // Fire and forget — ignore success/failure
        hook.call{ gas: HOOK_GAS_LIMIT }(data);
    }
}
