"""Unit tests for confidence-based transaction routing."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from sardis_v2_core.confidence_router import (
    ConfidenceRouter,
    ConfidenceLevel,
    ConfidenceThresholds,
    ApprovalWorkflow,
    ApprovalRequest,
)
from sardis_v2_core.spending_policy import SpendingPolicy


class TestConfidenceRouter:
    """Test confidence scoring and routing logic."""

    def test_high_confidence_auto_approve(self):
        """Test high confidence scores route to auto-approve."""
        policy = SpendingPolicy(
            agent_id="agent-123",
            limit_total=Decimal("10000"),
            limit_per_tx=Decimal("1000"),
        )

        router = ConfidenceRouter()

        # High confidence scenario: verified KYA, familiar merchant, normal amount
        transaction = {
            "amount": Decimal("50"),
            "merchant_id": "aws",
            "timestamp": datetime.now(timezone.utc),
        }

        history = [
            {"amount": Decimal("45"), "merchant_id": "aws", "timestamp": datetime.now(timezone.utc)}
            for _ in range(20)
        ]

        confidence = router.calculate_confidence(
            agent_id="agent-123",
            transaction=transaction,
            policy=policy,
            history=history,
            kya_level="attested",
            violation_count=0,
        )

        assert confidence.score >= 0.95
        assert confidence.level == ConfidenceLevel.AUTO_APPROVE

    def test_medium_confidence_manager_approval(self):
        """Test medium confidence routes to manager approval."""
        policy = SpendingPolicy(
            agent_id="agent-123",
            limit_total=Decimal("1000"),
            limit_per_tx=Decimal("500"),
        )
        policy._spent_total = Decimal("600")  # 60% budget used

        router = ConfidenceRouter()

        transaction = {
            "amount": Decimal("100"),
            "merchant_id": "new_merchant",
            "timestamp": datetime.now(timezone.utc),
        }

        history = [
            {"amount": Decimal("50"), "merchant_id": "other", "timestamp": datetime.now(timezone.utc)}
            for _ in range(5)
        ]

        confidence = router.calculate_confidence(
            agent_id="agent-123",
            transaction=transaction,
            policy=policy,
            history=history,
            kya_level="basic",
            violation_count=0,
        )

        assert 0.85 <= confidence.score < 0.95
        assert confidence.level == ConfidenceLevel.MANAGER_APPROVAL

    def test_low_confidence_multi_sig(self):
        """Test low confidence routes to multi-sig approval."""
        policy = SpendingPolicy(
            agent_id="agent-123",
            limit_total=Decimal("1000"),
            limit_per_tx=Decimal("500"),
        )
        policy._spent_total = Decimal("900")  # 90% budget used

        router = ConfidenceRouter()

        transaction = {
            "amount": Decimal("200"),  # Large relative to history
            "merchant_id": "unknown",
            "timestamp": datetime.now(timezone.utc),
        }

        history = [
            {"amount": Decimal("10"), "merchant_id": "other", "timestamp": datetime.now(timezone.utc)}
            for _ in range(3)
        ]

        confidence = router.calculate_confidence(
            agent_id="agent-123",
            transaction=transaction,
            policy=policy,
            history=history,
            kya_level="none",
            violation_count=2,
        )

        assert 0.70 <= confidence.score < 0.85
        assert confidence.level == ConfidenceLevel.MULTI_SIG

    def test_very_low_confidence_human_rewrite(self):
        """Test very low confidence routes to human rewrite."""
        policy = SpendingPolicy(
            agent_id="agent-123",
            limit_total=Decimal("100"),
            limit_per_tx=Decimal("100"),
        )
        policy._spent_total = Decimal("95")  # 95% budget used

        router = ConfidenceRouter()

        transaction = {
            "amount": Decimal("50"),
            "merchant_id": "suspicious",
            "timestamp": datetime.now(timezone.utc),
        }

        confidence = router.calculate_confidence(
            agent_id="agent-123",
            transaction=transaction,
            policy=policy,
            history=[],  # No history
            kya_level="none",
            violation_count=5,
        )

        assert confidence.score < 0.70
        assert confidence.level == ConfidenceLevel.HUMAN_REWRITE

    def test_kya_level_scoring(self):
        """Test KYA level affects confidence score."""
        policy = SpendingPolicy(
            agent_id="agent-123",
            limit_total=Decimal("10000"),
            limit_per_tx=Decimal("1000"),
        )

        router = ConfidenceRouter()
        transaction = {"amount": Decimal("100"), "merchant_id": "test"}

        # Test each KYA level
        conf_none = router.calculate_confidence("agent-123", transaction, policy, kya_level="none")
        conf_basic = router.calculate_confidence("agent-123", transaction, policy, kya_level="basic")
        conf_verified = router.calculate_confidence("agent-123", transaction, policy, kya_level="verified")
        conf_attested = router.calculate_confidence("agent-123", transaction, policy, kya_level="attested")

        # Higher KYA should give higher scores
        assert conf_none.score < conf_basic.score
        assert conf_basic.score < conf_verified.score
        assert conf_verified.score < conf_attested.score

    def test_merchant_familiarity_scoring(self):
        """Test merchant familiarity increases confidence."""
        policy = SpendingPolicy(
            agent_id="agent-123",
            limit_total=Decimal("10000"),
            limit_per_tx=Decimal("1000"),
        )

        router = ConfidenceRouter()

        # New merchant
        transaction_new = {"amount": Decimal("100"), "merchant_id": "new_merchant"}
        history_new = [
            {"amount": Decimal("100"), "merchant_id": "other"} for _ in range(5)
        ]

        # Familiar merchant
        transaction_familiar = {"amount": Decimal("100"), "merchant_id": "familiar"}
        history_familiar = [
            {"amount": Decimal("100"), "merchant_id": "familiar"} for _ in range(15)
        ]

        conf_new = router.calculate_confidence("agent-123", transaction_new, policy, history=history_new)
        conf_familiar = router.calculate_confidence("agent-123", transaction_familiar, policy, history=history_familiar)

        assert conf_familiar.score > conf_new.score

    def test_route_transaction_auto_approve(self):
        """Test routing decision for auto-approve."""
        router = ConfidenceRouter()

        confidence = router.calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=SpendingPolicy(agent_id="agent-123", limit_total=Decimal("10000")),
            kya_level="attested",
        )
        confidence.level = ConfidenceLevel.AUTO_APPROVE  # Force level for test

        routing = router.route_transaction(confidence)

        assert routing["approval_type"] == "auto_approve"
        assert routing["required_approvers"] == []
        assert routing["timeout"] == 0
        assert routing["quorum"] == 0

    def test_route_transaction_manager_approval(self):
        """Test routing decision for manager approval."""
        router = ConfidenceRouter()
        policy = SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000"))

        confidence = router.calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=policy,
            kya_level="basic",
        )
        confidence.level = ConfidenceLevel.MANAGER_APPROVAL  # Force level

        routing = router.route_transaction(confidence)

        assert routing["approval_type"] == "manager_approval"
        assert len(routing["required_approvers"]) == 1
        assert routing["timeout"] == 3600
        assert routing["quorum"] == 1

    def test_route_transaction_multi_sig(self):
        """Test routing decision for multi-sig."""
        router = ConfidenceRouter()
        policy = SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000"))

        confidence = router.calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=policy,
            kya_level="none",
        )
        confidence.level = ConfidenceLevel.MULTI_SIG  # Force level

        routing = router.route_transaction(confidence)

        assert routing["approval_type"] == "multi_sig"
        assert len(routing["required_approvers"]) == 2
        assert routing["timeout"] == 86400
        assert routing["quorum"] == 2

    def test_custom_thresholds(self):
        """Test custom confidence thresholds."""
        thresholds = ConfidenceThresholds(
            auto_approve=0.90,
            manager=0.75,
            multi_sig=0.60,
        )

        router = ConfidenceRouter(thresholds=thresholds)
        policy = SpendingPolicy(agent_id="agent-123", limit_total=Decimal("10000"))

        confidence = router.calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=policy,
            kya_level="verified",
        )

        # With lower thresholds, same transaction might get different tier
        level = thresholds.get_level(0.88)
        assert level == ConfidenceLevel.MANAGER_APPROVAL


class TestApprovalWorkflow:
    """Test approval request management."""

    @pytest.mark.asyncio
    async def test_request_approval(self):
        """Test creating approval request."""
        workflow = ApprovalWorkflow()

        confidence = ConfidenceRouter().calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000")),
        )

        request_id = await workflow.request_approval(
            transaction_id="tx-123",
            agent_id="agent-123",
            amount=Decimal("100"),
            confidence=confidence,
            approvers=["manager@company.com"],
            timeout=3600,
            quorum=1,
        )

        assert request_id == "tx-123"
        status = await workflow.get_approval_status("tx-123")
        assert status["status"] == "pending"

    @pytest.mark.asyncio
    async def test_approve_reaches_quorum(self):
        """Test approval reaching quorum."""
        workflow = ApprovalWorkflow()

        confidence = ConfidenceRouter().calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000")),
        )

        await workflow.request_approval(
            transaction_id="tx-123",
            agent_id="agent-123",
            amount=Decimal("100"),
            confidence=confidence,
            approvers=["approver1"],
            timeout=3600,
            quorum=1,
        )

        # Approve
        quorum_reached = await workflow.approve("tx-123", "approver1")

        assert quorum_reached is True
        assert await workflow.check_quorum("tx-123") is True

    @pytest.mark.asyncio
    async def test_multi_sig_quorum(self):
        """Test multi-signature approval requiring multiple approvers."""
        workflow = ApprovalWorkflow()

        confidence = ConfidenceRouter().calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000")),
        )

        await workflow.request_approval(
            transaction_id="tx-multi",
            agent_id="agent-123",
            amount=Decimal("500"),
            confidence=confidence,
            approvers=["approver1", "approver2", "approver3"],
            timeout=86400,
            quorum=2,
        )

        # First approval - quorum not reached
        quorum1 = await workflow.approve("tx-multi", "approver1")
        assert quorum1 is False

        # Second approval - quorum reached
        quorum2 = await workflow.approve("tx-multi", "approver2")
        assert quorum2 is True

        status = await workflow.get_approval_status("tx-multi")
        assert status["status"] == "approved"
        assert status["quorum_reached"] is True

    @pytest.mark.asyncio
    async def test_reject_approval(self):
        """Test rejecting approval request."""
        workflow = ApprovalWorkflow()

        confidence = ConfidenceRouter().calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000")),
        )

        await workflow.request_approval(
            transaction_id="tx-reject",
            agent_id="agent-123",
            amount=Decimal("100"),
            confidence=confidence,
            approvers=["approver1"],
            timeout=3600,
            quorum=1,
        )

        # Reject
        await workflow.reject("tx-reject", "approver1", "Suspicious transaction")

        status = await workflow.get_approval_status("tx-reject")
        assert status["status"] == "rejected"
        assert "approver1" in status["rejections"]
        assert status["rejections"]["approver1"]["reason"] == "Suspicious transaction"

    @pytest.mark.asyncio
    async def test_expired_approval_request(self):
        """Test approval request expiration."""
        import asyncio
        from datetime import timedelta

        workflow = ApprovalWorkflow()

        confidence = ConfidenceRouter().calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000")),
        )

        await workflow.request_approval(
            transaction_id="tx-expire",
            agent_id="agent-123",
            amount=Decimal("100"),
            confidence=confidence,
            approvers=["approver1"],
            timeout=0,  # Expires immediately
            quorum=1,
        )

        # Small delay to ensure expiration
        await asyncio.sleep(0.01)

        status = await workflow.get_approval_status("tx-expire")
        assert status["status"] == "expired"

    @pytest.mark.asyncio
    async def test_approve_after_expiration_raises_error(self):
        """Test approving expired request raises error."""
        import asyncio

        workflow = ApprovalWorkflow()

        confidence = ConfidenceRouter().calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000")),
        )

        await workflow.request_approval(
            transaction_id="tx-late",
            agent_id="agent-123",
            amount=Decimal("100"),
            confidence=confidence,
            approvers=["approver1"],
            timeout=0,
            quorum=1,
        )

        await asyncio.sleep(0.01)

        with pytest.raises(ValueError) as exc_info:
            await workflow.approve("tx-late", "approver1")

        assert "expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unauthorized_approver(self):
        """Test non-authorized approver cannot approve."""
        workflow = ApprovalWorkflow()

        confidence = ConfidenceRouter().calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000")),
        )

        await workflow.request_approval(
            transaction_id="tx-auth",
            agent_id="agent-123",
            amount=Decimal("100"),
            confidence=confidence,
            approvers=["approver1"],
            timeout=3600,
            quorum=1,
        )

        # Unauthorized approver
        quorum = await workflow.approve("tx-auth", "unauthorized")

        assert quorum is False
        assert await workflow.check_quorum("tx-auth") is False

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup of expired approval requests."""
        workflow = ApprovalWorkflow()

        confidence = ConfidenceRouter().calculate_confidence(
            agent_id="agent-123",
            transaction={"amount": Decimal("100")},
            policy=SpendingPolicy(agent_id="agent-123", limit_total=Decimal("1000")),
        )

        # Create expired request
        await workflow.request_approval(
            transaction_id="tx-clean",
            agent_id="agent-123",
            amount=Decimal("100"),
            confidence=confidence,
            approvers=["approver1"],
            timeout=0,
            quorum=1,
        )

        import asyncio
        await asyncio.sleep(0.01)

        # Cleanup
        count = workflow.cleanup_expired()

        assert count == 1
        status = await workflow.get_approval_status("tx-clean")
        assert status["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_approval_status_not_found(self):
        """Test status for non-existent request."""
        workflow = ApprovalWorkflow()

        status = await workflow.get_approval_status("nonexistent")

        assert status["status"] == "not_found"
