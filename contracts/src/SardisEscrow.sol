// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title SardisEscrow
 * @notice Escrow contract for trustless agent-to-agent payments
 * @dev Enables conditional payments between AI agents with dispute resolution
 * 
 * Features:
 * - Escrow deposits for A2A payments
 * - Multi-party approval (buyer, seller, arbiter)
 * - Time-locked releases
 * - Dispute resolution mechanism
 * - Milestone-based payments
 */
contract SardisEscrow is ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;

    // ============ Enums ============
    
    enum EscrowState {
        Created,
        Funded,
        Released,
        Disputed,
        Resolved,
        Refunded,
        Expired
    }
    
    // ============ Structs ============
    
    struct Escrow {
        address buyer;           // Agent buying the service
        address seller;          // Agent providing the service
        address token;           // Payment token
        uint256 amount;          // Total amount
        uint256 fee;             // Sardis fee
        uint256 createdAt;       // Creation timestamp
        uint256 deadline;        // Release deadline
        EscrowState state;       // Current state
        bytes32 conditionHash;   // Hash of release conditions
        bool buyerApproved;      // Buyer approved release
        bool sellerConfirmed;    // Seller confirmed delivery
        string description;      // Service description
    }
    
    struct Milestone {
        uint256 amount;
        bool completed;
        bool released;
    }
    
    // ============ State Variables ============
    
    /// @notice Counter for escrow IDs
    uint256 public escrowCounter;
    
    /// @notice Mapping of escrow ID to Escrow
    mapping(uint256 => Escrow) public escrows;
    
    /// @notice Mapping of escrow ID to milestones
    mapping(uint256 => Milestone[]) public milestones;
    
    /// @notice Sardis arbiter address for disputes
    address public arbiter;

    /// @notice Pending arbiter address awaiting timelock execution
    address public pendingArbiter;

    /// @notice Earliest timestamp when pending arbiter can be executed
    uint256 public pendingArbiterEta;

    /// @notice Timelock for arbiter changes
    uint256 public constant ARBITER_UPDATE_TIMELOCK = 2 days;
    
    /// @notice Fee percentage (basis points, 100 = 1%)
    uint256 public feeBps;
    
    /// @notice Minimum escrow amount
    uint256 public minAmount;
    
    /// @notice Maximum deadline extension (days)
    uint256 public maxDeadlineDays;
    
    // ============ Events ============
    
    event EscrowCreated(
        uint256 indexed escrowId,
        address indexed buyer,
        address indexed seller,
        address token,
        uint256 amount
    );
    
    event EscrowFunded(uint256 indexed escrowId);
    
    event DeliveryConfirmed(uint256 indexed escrowId);
    
    event ReleaseApproved(uint256 indexed escrowId);
    
    event EscrowReleased(
        uint256 indexed escrowId,
        uint256 amountToSeller,
        uint256 fee
    );
    
    event EscrowRefunded(uint256 indexed escrowId);

    event EscrowCancelled(uint256 indexed escrowId);
    
    event DisputeRaised(uint256 indexed escrowId, address indexed by);
    
    event DisputeResolved(
        uint256 indexed escrowId,
        uint256 buyerAmount,
        uint256 sellerAmount
    );
    
    event MilestoneCompleted(uint256 indexed escrowId, uint256 indexed milestoneIndex);

    event MilestoneReleased(uint256 indexed escrowId, uint256 indexed milestoneIndex);

    event ConditionVerified(uint256 indexed escrowId, bytes32 indexed conditionHash);

    event ReleasedWithCondition(uint256 indexed escrowId, bytes32 indexed conditionHash);

    event ArbiterUpdateProposed(
        address indexed currentArbiter,
        address indexed pendingArbiter,
        uint256 executeAfter
    );

    event ArbiterUpdateExecuted(address indexed oldArbiter, address indexed newArbiter);

    event ArbiterUpdateCancelled(address indexed pendingArbiter);
    
    // ============ Modifiers ============
    
    modifier onlyBuyer(uint256 escrowId) {
        require(msg.sender == escrows[escrowId].buyer, "Only buyer");
        _;
    }
    
    modifier onlySeller(uint256 escrowId) {
        require(msg.sender == escrows[escrowId].seller, "Only seller");
        _;
    }
    
    modifier onlyArbiter() {
        require(msg.sender == arbiter, "Only arbiter");
        _;
    }
    
    modifier inState(uint256 escrowId, EscrowState state) {
        require(escrows[escrowId].state == state, "Invalid state");
        _;
    }
    
    // ============ Constructor ============
    
    constructor(
        address _arbiter,
        uint256 _feeBps,
        uint256 _minAmount,
        uint256 _maxDeadlineDays
    ) Ownable(msg.sender) {
        require(_arbiter != address(0), "Invalid arbiter");
        require(_feeBps <= 500, "Fee too high"); // Max 5%

        arbiter = _arbiter;
        feeBps = _feeBps;
        minAmount = _minAmount;
        maxDeadlineDays = _maxDeadlineDays;
    }
    
    // ============ Escrow Creation ============
    
    /**
     * @notice Create a new escrow
     * @param seller The seller address
     * @param token Payment token
     * @param amount Payment amount
     * @param deadline When the escrow expires
     * @param conditionHash Hash of delivery conditions
     * @param description Service description
     */
    function createEscrow(
        address seller,
        address token,
        uint256 amount,
        uint256 deadline,
        bytes32 conditionHash,
        string calldata description
    ) external returns (uint256 escrowId) {
        return _createEscrow(msg.sender, seller, token, amount, deadline, conditionHash, description);
    }

    /**
     * @notice Create escrow with milestones
     * @param seller The seller address
     * @param token Payment token
     * @param milestoneAmounts Array of amounts for each milestone
     * @param deadline When the escrow expires
     * @param conditionHash Hash of delivery conditions
     * @param description Service description
     */
    function createEscrowWithMilestones(
        address seller,
        address token,
        uint256[] calldata milestoneAmounts,
        uint256 deadline,
        bytes32 conditionHash,
        string calldata description
    ) external returns (uint256 escrowId) {
        require(milestoneAmounts.length > 0, "No milestones");
        require(milestoneAmounts.length <= 20, "Too many milestones");

        uint256 totalAmount = 0;
        for (uint256 i = 0; i < milestoneAmounts.length; i++) {
            require(milestoneAmounts[i] > 0, "Zero milestone amount");
            totalAmount += milestoneAmounts[i];
        }

        // Use internal function to preserve msg.sender as buyer
        escrowId = _createEscrow(msg.sender, seller, token, totalAmount, deadline, conditionHash, description);

        for (uint256 i = 0; i < milestoneAmounts.length; i++) {
            milestones[escrowId].push(Milestone({
                amount: milestoneAmounts[i],
                completed: false,
                released: false
            }));
        }
    }

    /**
     * @notice Internal function to create escrow with explicit buyer
     */
    function _createEscrow(
        address buyer,
        address seller,
        address token,
        uint256 amount,
        uint256 deadline,
        bytes32 conditionHash,
        string calldata description
    ) internal returns (uint256 escrowId) {
        require(seller != address(0) && seller != buyer, "Invalid seller");
        require(amount >= minAmount, "Amount too low");
        require(deadline > block.timestamp, "Invalid deadline");
        require(deadline <= block.timestamp + maxDeadlineDays * 1 days, "Deadline too far");

        uint256 fee = (amount * feeBps) / 10000;

        escrowId = escrowCounter++;

        escrows[escrowId] = Escrow({
            buyer: buyer,
            seller: seller,
            token: token,
            amount: amount,
            fee: fee,
            createdAt: block.timestamp,
            deadline: deadline,
            state: EscrowState.Created,
            conditionHash: conditionHash,
            buyerApproved: false,
            sellerConfirmed: false,
            description: description
        });

        emit EscrowCreated(escrowId, buyer, seller, token, amount);
    }
    
    // ============ Escrow Lifecycle ============
    
    /**
     * @notice Fund the escrow (buyer deposits tokens)
     */
    function fundEscrow(uint256 escrowId) 
        external 
        onlyBuyer(escrowId)
        inState(escrowId, EscrowState.Created)
        nonReentrant
    {
        Escrow storage e = escrows[escrowId];
        
        uint256 totalRequired = e.amount + e.fee;
        IERC20(e.token).safeTransferFrom(msg.sender, address(this), totalRequired);
        
        e.state = EscrowState.Funded;
        
        emit EscrowFunded(escrowId);
    }
    
    /**
     * @notice Seller confirms delivery
     */
    function confirmDelivery(uint256 escrowId)
        external
        onlySeller(escrowId)
        inState(escrowId, EscrowState.Funded)
    {
        escrows[escrowId].sellerConfirmed = true;
        
        emit DeliveryConfirmed(escrowId);
    }
    
    /**
     * @notice Buyer approves release
     * @dev SECURITY: nonReentrant is required because _release() performs external
     *      token transfers. Without it, a malicious token contract could re-enter
     *      and drain funds or manipulate escrow state.
     */
    function approveRelease(uint256 escrowId)
        external
        onlyBuyer(escrowId)
        inState(escrowId, EscrowState.Funded)
        nonReentrant
    {
        Escrow storage e = escrows[escrowId];
        e.buyerApproved = true;

        emit ReleaseApproved(escrowId);

        // If both parties agree, release funds
        if (e.sellerConfirmed) {
            _release(escrowId);
        }
    }
    
    /**
     * @notice Release funds to seller (after approval)
     */
    function release(uint256 escrowId)
        external
        inState(escrowId, EscrowState.Funded)
        nonReentrant
    {
        Escrow storage e = escrows[escrowId];
        require(e.buyerApproved && e.sellerConfirmed, "Not approved by both parties");

        _release(escrowId);
    }

    /**
     * @notice Release funds with condition verification
     * @dev Allows release by providing condition data that hashes to stored conditionHash.
     *      SECURITY: Requires conditionHash to be non-zero. Without this check,
     *      any authorized party could unilaterally release funds by calling this
     *      function on escrows with no condition set, bypassing the mutual-approval
     *      flow (buyerApproved + sellerConfirmed) required by release().
     * @param escrowId The escrow to release
     * @param conditionData The condition data that should hash to conditionHash
     */
    function releaseWithCondition(
        uint256 escrowId,
        bytes calldata conditionData
    )
        external
        inState(escrowId, EscrowState.Funded)
        nonReentrant
    {
        Escrow storage e = escrows[escrowId];
        require(msg.sender == e.buyer || msg.sender == e.seller || msg.sender == arbiter, "Not authorized");

        // SECURITY: Require that a condition was actually set for this escrow.
        // If no condition was set, parties must use the standard approval flow.
        require(e.conditionHash != bytes32(0), "No condition set - use standard release");

        // Verify condition data matches the stored hash
        require(keccak256(conditionData) == e.conditionHash, "Condition not met");

        emit ReleasedWithCondition(escrowId, e.conditionHash);
        _release(escrowId);
    }
    
    /**
     * @notice Refund buyer (before seller confirms or if deadline passed)
     */
    function refund(uint256 escrowId)
        external
        onlyBuyer(escrowId)
        inState(escrowId, EscrowState.Funded)
        nonReentrant
    {
        Escrow storage e = escrows[escrowId];
        require(!e.sellerConfirmed, "Seller already confirmed");
        require(block.timestamp > e.deadline, "Deadline not passed");

        _refund(escrowId);
    }

    /**
     * @notice Cancel an unfunded escrow
     * @dev Only buyer can cancel. Escrow must be in Created state (not yet funded).
     */
    function cancelEscrow(uint256 escrowId)
        external
        onlyBuyer(escrowId)
        inState(escrowId, EscrowState.Created)
    {
        escrows[escrowId].state = EscrowState.Expired;

        emit EscrowCancelled(escrowId);
    }
    
    // ============ Milestone Functions ============
    
    /**
     * @notice Mark a milestone as completed (seller)
     */
    function completeMilestone(uint256 escrowId, uint256 milestoneIndex)
        external
        onlySeller(escrowId)
    {
        require(milestoneIndex < milestones[escrowId].length, "Invalid milestone");
        require(!milestones[escrowId][milestoneIndex].completed, "Already completed");
        
        milestones[escrowId][milestoneIndex].completed = true;
        
        emit MilestoneCompleted(escrowId, milestoneIndex);
    }
    
    /**
     * @notice Release a milestone payment (buyer approval)
     * @dev Fee is calculated proportionally based on the escrow's stored fee
     */
    function releaseMilestone(uint256 escrowId, uint256 milestoneIndex)
        external
        onlyBuyer(escrowId)
        inState(escrowId, EscrowState.Funded)
        nonReentrant
    {
        require(milestoneIndex < milestones[escrowId].length, "Invalid milestone");
        Milestone storage m = milestones[escrowId][milestoneIndex];
        require(m.completed, "Milestone not completed");
        require(!m.released, "Already released");

        m.released = true;

        Escrow storage e = escrows[escrowId];

        // Calculate proportional fee based on stored fee (consistent with deposit)
        // milestoneFee = (m.amount / e.amount) * e.fee
        uint256 milestoneFee = (m.amount * e.fee) / e.amount;
        uint256 sellerAmount = m.amount;

        IERC20(e.token).safeTransfer(e.seller, sellerAmount);
        IERC20(e.token).safeTransfer(owner(), milestoneFee);

        emit MilestoneReleased(escrowId, milestoneIndex);

        // Check if all milestones are released, if so transition state
        if (_allMilestonesReleased(escrowId)) {
            e.state = EscrowState.Released;
            emit EscrowReleased(escrowId, e.amount, e.fee);
        }
    }

    /**
     * @notice Check if all milestones for an escrow are released
     */
    function _allMilestonesReleased(uint256 escrowId) internal view returns (bool) {
        Milestone[] storage ms = milestones[escrowId];
        if (ms.length == 0) return false;

        for (uint256 i = 0; i < ms.length; i++) {
            if (!ms[i].released) {
                return false;
            }
        }
        return true;
    }
    
    // ============ Dispute Functions ============
    
    /**
     * @notice Raise a dispute
     */
    function raiseDispute(uint256 escrowId)
        external
        inState(escrowId, EscrowState.Funded)
    {
        Escrow storage e = escrows[escrowId];
        require(
            msg.sender == e.buyer || msg.sender == e.seller,
            "Not a party to escrow"
        );
        
        e.state = EscrowState.Disputed;
        
        emit DisputeRaised(escrowId, msg.sender);
    }
    
    /**
     * @notice Resolve dispute (arbiter only)
     * @param buyerPercent Percentage to return to buyer (0-100)
     */
    function resolveDispute(uint256 escrowId, uint256 buyerPercent)
        external
        onlyArbiter
        inState(escrowId, EscrowState.Disputed)
        nonReentrant
    {
        require(buyerPercent <= 100, "Invalid percentage");
        
        Escrow storage e = escrows[escrowId];
        
        uint256 total = e.amount;
        uint256 buyerAmount = (total * buyerPercent) / 100;
        uint256 sellerAmount = total - buyerAmount;
        
        e.state = EscrowState.Resolved;
        
        if (buyerAmount > 0) {
            IERC20(e.token).safeTransfer(e.buyer, buyerAmount);
        }
        if (sellerAmount > 0) {
            IERC20(e.token).safeTransfer(e.seller, sellerAmount);
        }
        
        // Fee goes to Sardis regardless of outcome
        IERC20(e.token).safeTransfer(owner(), e.fee);
        
        emit DisputeResolved(escrowId, buyerAmount, sellerAmount);
    }
    
    // ============ Internal Functions ============
    
    function _release(uint256 escrowId) internal {
        Escrow storage e = escrows[escrowId];
        e.state = EscrowState.Released;
        
        uint256 sellerAmount = e.amount;
        
        IERC20(e.token).safeTransfer(e.seller, sellerAmount);
        IERC20(e.token).safeTransfer(owner(), e.fee);
        
        emit EscrowReleased(escrowId, sellerAmount, e.fee);
    }
    
    function _refund(uint256 escrowId) internal {
        Escrow storage e = escrows[escrowId];
        e.state = EscrowState.Refunded;
        
        // Refund full amount including fee
        uint256 refundAmount = e.amount + e.fee;
        IERC20(e.token).safeTransfer(e.buyer, refundAmount);
        
        emit EscrowRefunded(escrowId);
    }
    
    // ============ Admin Functions ============
    
    function setArbiter(address _arbiter) external onlyOwner {
        // Backwards-compatible alias: setting arbiter now requires timelocked execution.
        proposeArbiter(_arbiter);
    }

    function proposeArbiter(address _arbiter) public onlyOwner {
        require(_arbiter != address(0), "Invalid arbiter");
        require(_arbiter != arbiter, "Arbiter unchanged");
        pendingArbiter = _arbiter;
        pendingArbiterEta = block.timestamp + ARBITER_UPDATE_TIMELOCK;
        emit ArbiterUpdateProposed(arbiter, _arbiter, pendingArbiterEta);
    }

    function executeArbiterUpdate() external onlyOwner {
        require(pendingArbiter != address(0), "No pending arbiter");
        require(block.timestamp >= pendingArbiterEta, "Timelock not expired");

        address oldArbiter = arbiter;
        address newArbiter = pendingArbiter;

        arbiter = newArbiter;
        pendingArbiter = address(0);
        pendingArbiterEta = 0;

        emit ArbiterUpdateExecuted(oldArbiter, newArbiter);
    }

    function cancelArbiterUpdate() external onlyOwner {
        require(pendingArbiter != address(0), "No pending arbiter");
        address cancelled = pendingArbiter;
        pendingArbiter = address(0);
        pendingArbiterEta = 0;
        emit ArbiterUpdateCancelled(cancelled);
    }
    
    function setFeeBps(uint256 _feeBps) external onlyOwner {
        require(_feeBps <= 500, "Fee too high");
        feeBps = _feeBps;
    }
    
    function setMinAmount(uint256 _minAmount) external onlyOwner {
        minAmount = _minAmount;
    }
    
    // ============ View Functions ============
    
    function getEscrow(uint256 escrowId) external view returns (Escrow memory) {
        return escrows[escrowId];
    }

    /**
     * @notice Verify if condition data matches the stored condition hash
     * @param escrowId The escrow to check
     * @param conditionData The condition data to verify
     * @return valid True if condition matches or no condition was set
     * @return reason Description of verification result
     */
    function verifyCondition(
        uint256 escrowId,
        bytes calldata conditionData
    ) external view returns (bool valid, string memory reason) {
        Escrow storage e = escrows[escrowId];

        if (e.conditionHash == bytes32(0)) {
            return (true, "No condition set");
        }

        bytes32 dataHash = keccak256(conditionData);
        if (dataHash == e.conditionHash) {
            return (true, "Condition verified");
        }

        return (false, "Condition hash mismatch");
    }

    /**
     * @notice Check if an escrow has a release condition set
     * @param escrowId The escrow to check
     * @return hasCondition True if a condition hash is set
     */
    function hasReleaseCondition(uint256 escrowId) external view returns (bool) {
        return escrows[escrowId].conditionHash != bytes32(0);
    }
    
    function getMilestones(uint256 escrowId) external view returns (Milestone[] memory) {
        return milestones[escrowId];
    }
    
    function getEscrowCount() external view returns (uint256) {
        return escrowCounter;
    }
}
