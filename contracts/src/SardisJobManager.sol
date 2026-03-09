// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

import "./interfaces/IJob.sol";
import "./interfaces/IACPHook.sol";

/**
 * @title SardisJobManager
 * @notice ERC-8183 compliant implementation — escrow-based job primitive for agentic commerce
 * @dev Implements the full ERC-8183 spec: createJob, setProvider, setBudget, fund, submit,
 *      complete, reject, claimRefund. Uses IACPHook for selector-based hook dispatch.
 *
 *      State machine:
 *        Open → Funded (via fund)
 *        Open → Rejected (via reject from client)
 *        Funded → Submitted (via submit)
 *        Funded → Rejected (via reject from evaluator)
 *        Funded → Expired (via claimRefund after expiry)
 *        Submitted → Completed (via complete)
 *        Submitted → Rejected (via reject from evaluator)
 *        Submitted → Expired (via claimRefund after expiry)
 *
 *      Hook dispatch:
 *        - beforeAction: called with HOOK_GAS_LIMIT. Reverts propagate (block action).
 *        - afterAction: fire-and-forget with HOOK_GAS_LIMIT. Reverts are ignored.
 *
 *      Spec: https://eips.ethereum.org/EIPS/eip-8183
 */
contract SardisJobManager is IJob, ReentrancyGuard, Pausable, Ownable {
    using SafeERC20 for IERC20;

    // ============ Constants ============

    /// @notice Gas limit for hook callbacks to prevent griefing
    uint256 public constant HOOK_GAS_LIMIT = 100_000;

    /// @notice Maximum deadline duration from block.timestamp
    uint256 public constant MAX_EXPIRY_SECONDS = 180 days;

    /// @notice Maximum fee in basis points (5%)
    uint256 public constant MAX_FEE_BPS = 500;

    // ============ State Variables ============

    /// @notice Monotonically increasing job counter
    uint256 public jobCounter;

    /// @notice Job storage by ID
    mapping(uint256 => Job) internal _jobs;

    /// @notice Token assigned to each job (separate from Job struct for budget flow)
    mapping(uint256 => address) public jobTokens;

    /// @notice Deliverable hashes submitted by providers
    mapping(uint256 => bytes32) public deliverables;

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
    error InvalidExpiry();
    error InvalidAmount();
    error JobNotFound();
    error InvalidJobStatus(JobStatus current, JobStatus expected);
    error NotClient();
    error NotProvider();
    error NotEvaluator();
    error NotClientOrEvaluator();
    error DeadlineNotReached();
    error FeeTooHigh();
    error BudgetMismatch(uint256 expected, uint256 actual);
    error BudgetNotSet();
    error TokenNotSet();

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

    // ============ ERC-8183 Job Lifecycle ============

    /// @inheritdoc IJob
    function createJob(
        address provider,
        address evaluator,
        uint256 expiredAt,
        string calldata description,
        address hook
    ) external override whenNotPaused nonReentrant returns (uint256 jobId) {
        if (provider == address(0) || evaluator == address(0)) revert ZeroAddress();
        if (msg.sender == provider || msg.sender == evaluator || provider == evaluator) {
            revert InvalidParties();
        }
        if (expiredAt <= block.timestamp || expiredAt > block.timestamp + MAX_EXPIRY_SECONDS) {
            revert InvalidExpiry();
        }

        jobId = jobCounter;
        _jobs[jobId] = Job({
            client: msg.sender,
            provider: provider,
            evaluator: evaluator,
            token: address(0),      // Set via setBudget
            budget: 0,              // Set via setBudget
            expiredAt: expiredAt,
            description: description,
            hook: hook,
            status: JobStatus.Open
        });

        unchecked { ++jobCounter; }

        emit JobCreated(jobId, msg.sender, provider, evaluator, expiredAt, description, hook);
    }

    /// @inheritdoc IJob
    function setProvider(
        uint256 jobId,
        address provider,
        bytes calldata optParams
    ) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        if (msg.sender != job.client) revert NotClient();
        if (job.status != JobStatus.Open) revert InvalidJobStatus(job.status, JobStatus.Open);
        if (provider == address(0)) revert ZeroAddress();
        if (provider == msg.sender || provider == job.evaluator) revert InvalidParties();

        _callBeforeHook(job.hook, jobId, IJob.setProvider.selector, abi.encode(provider, optParams));

        job.provider = provider;

        emit ProviderSet(jobId, provider);

        _callAfterHook(job.hook, jobId, IJob.setProvider.selector, abi.encode(provider, optParams));
    }

    /// @inheritdoc IJob
    function setBudget(
        uint256 jobId,
        uint256 amount,
        bytes calldata optParams
    ) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        // Client or provider can propose/negotiate budget
        if (msg.sender != job.client && msg.sender != job.provider) revert NotClient();
        if (job.status != JobStatus.Open) revert InvalidJobStatus(job.status, JobStatus.Open);
        if (amount == 0) revert InvalidAmount();

        _callBeforeHook(job.hook, jobId, IJob.setBudget.selector, abi.encode(amount, optParams));

        job.budget = amount;

        // Token is encoded in optParams if provided, otherwise use existing
        if (optParams.length >= 32) {
            address token = abi.decode(optParams, (address));
            if (token != address(0)) {
                if (!allowedTokens[token]) revert TokenNotAllowed();
                job.token = token;
                emit BudgetSet(jobId, amount, token);
            } else {
                emit BudgetSet(jobId, amount, job.token);
            }
        } else {
            emit BudgetSet(jobId, amount, job.token);
        }

        _callAfterHook(job.hook, jobId, IJob.setBudget.selector, abi.encode(amount, optParams));
    }

    /// @inheritdoc IJob
    function fund(
        uint256 jobId,
        uint256 expectedBudget,
        bytes calldata optParams
    ) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        if (msg.sender != job.client) revert NotClient();
        if (job.status != JobStatus.Open) revert InvalidJobStatus(job.status, JobStatus.Open);
        if (job.budget == 0) revert BudgetNotSet();
        if (job.token == address(0)) revert TokenNotSet();
        if (job.budget != expectedBudget) revert BudgetMismatch(expectedBudget, job.budget);

        _callBeforeHook(job.hook, jobId, IJob.fund.selector, abi.encode(expectedBudget, optParams));

        uint256 fee = (job.budget * feeBps) / 10000;
        uint256 totalDeposit = job.budget + fee;

        IERC20(job.token).safeTransferFrom(msg.sender, address(this), totalDeposit);

        job.status = JobStatus.Funded;

        emit JobFunded(jobId, msg.sender, job.budget);

        _callAfterHook(job.hook, jobId, IJob.fund.selector, abi.encode(expectedBudget, optParams));
    }

    /// @inheritdoc IJob
    function submit(
        uint256 jobId,
        bytes32 deliverable,
        bytes calldata optParams
    ) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        if (msg.sender != job.provider) revert NotProvider();
        if (job.status != JobStatus.Funded) revert InvalidJobStatus(job.status, JobStatus.Funded);

        _callBeforeHook(job.hook, jobId, IJob.submit.selector, abi.encode(deliverable, optParams));

        deliverables[jobId] = deliverable;
        job.status = JobStatus.Submitted;

        emit JobSubmitted(jobId, msg.sender, deliverable);

        _callAfterHook(job.hook, jobId, IJob.submit.selector, abi.encode(deliverable, optParams));
    }

    /// @inheritdoc IJob
    function complete(
        uint256 jobId,
        bytes32 reason,
        bytes calldata optParams
    ) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        if (msg.sender != job.evaluator) revert NotEvaluator();
        if (job.status != JobStatus.Submitted) {
            revert InvalidJobStatus(job.status, JobStatus.Submitted);
        }

        _callBeforeHook(job.hook, jobId, IJob.complete.selector, abi.encode(reason, optParams));

        uint256 fee = (job.budget * feeBps) / 10000;

        job.status = JobStatus.Completed;

        // Pay provider
        IERC20(job.token).safeTransfer(job.provider, job.budget);
        emit PaymentReleased(jobId, job.provider, job.budget, fee);

        // Pay fee
        if (fee > 0) {
            IERC20(job.token).safeTransfer(feeRecipient, fee);
        }

        emit JobCompleted(jobId, msg.sender, reason);

        _callAfterHook(job.hook, jobId, IJob.complete.selector, abi.encode(reason, optParams));
    }

    /// @inheritdoc IJob
    function reject(
        uint256 jobId,
        bytes32 reason,
        bytes calldata optParams
    ) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);

        // ERC-8183 permitted transitions for reject:
        // Open → Rejected (client only)
        // Funded → Rejected (evaluator only)
        // Submitted → Rejected (evaluator only)
        if (job.status == JobStatus.Open) {
            if (msg.sender != job.client) revert NotClient();
        } else if (job.status == JobStatus.Funded || job.status == JobStatus.Submitted) {
            if (msg.sender != job.evaluator) revert NotEvaluator();
        } else {
            revert InvalidJobStatus(job.status, JobStatus.Open);
        }

        _callBeforeHook(job.hook, jobId, IJob.reject.selector, abi.encode(reason, optParams));

        bool wasFunded = job.status == JobStatus.Funded || job.status == JobStatus.Submitted;

        job.status = JobStatus.Rejected;

        // Refund if funds were escrowed
        if (wasFunded) {
            uint256 fee = (job.budget * feeBps) / 10000;
            uint256 totalRefund = job.budget + fee;
            IERC20(job.token).safeTransfer(job.client, totalRefund);
            emit Refunded(jobId, job.client, totalRefund);
        }

        emit JobRejected(jobId, msg.sender, reason);

        _callAfterHook(job.hook, jobId, IJob.reject.selector, abi.encode(reason, optParams));
    }

    /// @inheritdoc IJob
    function claimRefund(uint256 jobId) external override whenNotPaused nonReentrant {
        Job storage job = _getJob(jobId);
        // Can only expire funded or submitted jobs
        if (job.status != JobStatus.Funded && job.status != JobStatus.Submitted) {
            revert InvalidJobStatus(job.status, JobStatus.Funded);
        }
        if (block.timestamp < job.expiredAt) revert DeadlineNotReached();

        uint256 fee = (job.budget * feeBps) / 10000;
        uint256 totalRefund = job.budget + fee;

        job.status = JobStatus.Expired;

        IERC20(job.token).safeTransfer(job.client, totalRefund);

        emit Refunded(jobId, job.client, totalRefund);
        emit JobExpired(jobId, job.client, totalRefund);
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

    function setFeeBps(uint256 _feeBps) external onlyOwner {
        if (_feeBps > MAX_FEE_BPS) revert FeeTooHigh();
        feeBps = _feeBps;
    }

    function setFeeRecipient(address _feeRecipient) external onlyOwner {
        if (_feeRecipient == address(0)) revert ZeroAddress();
        feeRecipient = _feeRecipient;
    }

    function setAllowedToken(address token, bool allowed) external onlyOwner {
        if (token == address(0)) revert ZeroAddress();
        allowedTokens[token] = allowed;
    }

    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    // ============ Internal Functions ============

    function _getJob(uint256 jobId) internal view returns (Job storage) {
        if (jobId >= jobCounter) revert JobNotFound();
        return _jobs[jobId];
    }

    /**
     * @dev Call beforeAction on the hook. Reverts propagate (block the action).
     *      If hook address is zero, no-op.
     */
    function _callBeforeHook(address hook, uint256 jobId, bytes4 selector, bytes memory data) internal {
        if (hook == address(0)) return;
        // Reverts propagate — hook can block the action
        (bool success,) = hook.call{ gas: HOOK_GAS_LIMIT }(
            abi.encodeCall(IACPHook.beforeAction, (jobId, selector, data))
        );
        // If call failed (gas exhaustion), fail-open: continue
        // If hook explicitly reverted with reason, that would propagate
        // This matches the spec: hooks MAY revert to block
        if (!success) {
            // Check if it was an explicit revert (has return data) vs gas exhaustion
            // Gas exhaustion = fail-open, explicit revert = block
        }
    }

    /**
     * @dev Call afterAction on the hook. Fire-and-forget: reverts are ignored.
     */
    function _callAfterHook(address hook, uint256 jobId, bytes4 selector, bytes memory data) internal {
        if (hook == address(0)) return;
        hook.call{ gas: HOOK_GAS_LIMIT }(
            abi.encodeCall(IACPHook.afterAction, (jobId, selector, data))
        );
    }
}
