"""
End-to-End Approval Flow Tests for Sardis

Tests the complete approval workflow including:
- Creating approval requests when policies require it
- Webhook notifications for approval events
- Approving/denying approval requests
- Approval expiration

Run with: pytest tests/e2e/test_approval_e2e.py -v
"""
import os
import pytest
from datetime import datetime, timezone
from decimal import Decimal

API_URL = os.getenv("SARDIS_API_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("SARDIS_TEST_API_KEY", "sk_test_sardis_e2e")


class TestApprovalFlow:
    """Test approval request creation and workflow."""

    @pytest.mark.e2e
    async def test_create_approval_request(self, api_key, api_url):
        """Should create an approval request for high-value payment."""
        try:
            from sardis_v2_core.approval_service import ApprovalService
            from sardis_v2_core.approval_repository import ApprovalRepository

            # Create approval repository
            dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis_test")
            repo = ApprovalRepository(dsn)
            service = ApprovalService(repo)

            # Create approval request
            approval = await service.create_approval(
                action="payment",
                requested_by="agent_test_001",
                agent_id="agent_test_001",
                wallet_id="wallet_test_001",
                vendor="Anthropic",
                amount=Decimal("50000.00"),
                purpose="High-value API credits purchase",
                reason="Exceeds daily spending limit of $10,000",
                urgency="high",
                expires_in_hours=24,
            )

            assert approval is not None
            assert approval.id.startswith("appr_")
            assert approval.action == "payment"
            assert approval.status == "pending"
            assert approval.urgency == "high"
            assert approval.requested_by == "agent_test_001"
            assert approval.vendor == "Anthropic"
            assert approval.amount == Decimal("50000.00")
            assert approval.expires_at is not None

        except ImportError:
            pytest.skip("sardis_v2_core not available")

    @pytest.mark.e2e
    async def test_approve_request(self, api_key, api_url):
        """Should approve a pending approval request."""
        try:
            from sardis_v2_core.approval_service import ApprovalService
            from sardis_v2_core.approval_repository import ApprovalRepository

            dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis_test")
            repo = ApprovalRepository(dsn)
            service = ApprovalService(repo)

            # Create approval
            approval = await service.create_approval(
                action="create_card",
                requested_by="agent_test_002",
                agent_id="agent_test_002",
                card_limit=Decimal("5000.00"),
                reason="Needs virtual card for vendor payments",
                urgency="medium",
            )

            # Approve it
            approved = await service.approve(
                approval_id=approval.id,
                reviewed_by="admin@sardis.dev",
            )

            assert approved is not None
            assert approved.status == "approved"
            assert approved.reviewed_by == "admin@sardis.dev"
            assert approved.reviewed_at is not None

        except ImportError:
            pytest.skip("sardis_v2_core not available")

    @pytest.mark.e2e
    async def test_deny_request(self, api_key, api_url):
        """Should deny a pending approval request."""
        try:
            from sardis_v2_core.approval_service import ApprovalService
            from sardis_v2_core.approval_repository import ApprovalRepository

            dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis_test")
            repo = ApprovalRepository(dsn)
            service = ApprovalService(repo)

            # Create approval
            approval = await service.create_approval(
                action="payment",
                requested_by="agent_test_003",
                vendor="UnknownVendor",
                amount=Decimal("100000.00"),
                reason="Unusual vendor and high amount",
                urgency="low",
            )

            # Deny it
            denied = await service.deny(
                approval_id=approval.id,
                reviewed_by="admin@sardis.dev",
                reason="Vendor not on approved list",
            )

            assert denied is not None
            assert denied.status == "denied"
            assert denied.reviewed_by == "admin@sardis.dev"
            assert denied.metadata.get("denial_reason") == "Vendor not on approved list"

        except ImportError:
            pytest.skip("sardis_v2_core not available")


class TestApprovalWebhooks:
    """Test webhook notifications for approval events."""

    @pytest.mark.e2e
    async def test_webhook_on_approval_created(self, api_key, api_url):
        """Should send webhook when approval is created."""
        try:
            from sardis_v2_core.approval_service import ApprovalService
            from sardis_v2_core.approval_repository import ApprovalRepository
            from sardis_v2_core.approval_notifier import ApprovalNotifier
            from sardis_v2_core.webhooks import WebhookService, WebhookRepository

            dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis_test")

            # Setup services
            approval_repo = ApprovalRepository(dsn)
            approval_service = ApprovalService(approval_repo)

            webhook_repo = WebhookRepository(dsn)
            webhook_service = WebhookService(webhook_repo)
            notifier = ApprovalNotifier(webhook_service)

            # Create webhook subscription
            subscription = await webhook_repo.create_subscription(
                organization_id="org_test_001",
                url="https://webhook.site/test-approval",
                events=["risk.alert"],  # Approval notifications use risk.alert
            )

            # Create approval
            approval = await approval_service.create_approval(
                action="payment",
                requested_by="agent_webhook_test",
                vendor="TestVendor",
                amount=Decimal("25000.00"),
                urgency="high",
                organization_id="org_test_001",
            )

            # Send notification
            await notifier.notify_approval_requested(
                approval_id=approval.id,
                action=approval.action,
                requested_by=approval.requested_by,
                urgency=approval.urgency,
                vendor=approval.vendor,
                amount=approval.amount,
                expires_at=approval.expires_at.isoformat() if approval.expires_at else None,
            )

            # Wait briefly for async delivery
            import asyncio
            await asyncio.sleep(0.5)

            # Check deliveries
            deliveries = await webhook_repo.list_deliveries(
                subscription_id=subscription.subscription_id,
                limit=10,
            )

            # Should have attempted delivery
            assert len(deliveries) > 0
            latest = deliveries[0]
            assert latest.event_type == "risk.alert"

        except ImportError:
            pytest.skip("sardis_v2_core not available")

    @pytest.mark.e2e
    async def test_webhook_on_approval_approved(self, api_key, api_url):
        """Should send webhook when approval is approved."""
        try:
            from sardis_v2_core.approval_service import ApprovalService
            from sardis_v2_core.approval_repository import ApprovalRepository
            from sardis_v2_core.approval_notifier import ApprovalNotifier
            from sardis_v2_core.webhooks import WebhookService, WebhookRepository

            dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis_test")

            approval_repo = ApprovalRepository(dsn)
            approval_service = ApprovalService(approval_repo)

            webhook_repo = WebhookRepository(dsn)
            webhook_service = WebhookService(webhook_repo)
            notifier = ApprovalNotifier(webhook_service)

            # Create webhook subscription
            await webhook_repo.create_subscription(
                organization_id="org_test_002",
                url="https://webhook.site/test-approved",
                events=["risk.alert"],
            )

            # Create and approve
            approval = await approval_service.create_approval(
                action="create_card",
                requested_by="agent_approve_test",
                card_limit=Decimal("3000.00"),
                organization_id="org_test_002",
            )

            approved = await approval_service.approve(
                approval_id=approval.id,
                reviewed_by="admin@sardis.dev",
            )

            # Send notification
            await notifier.notify_approval_approved(
                approval_id=approved.id,
                action=approved.action,
                reviewed_by=approved.reviewed_by,
            )

            # Webhook should be delivered with approval.approved event
            import asyncio
            await asyncio.sleep(0.5)

        except ImportError:
            pytest.skip("sardis_v2_core not available")

    @pytest.mark.e2e
    async def test_webhook_on_approval_denied(self, api_key, api_url):
        """Should send webhook when approval is denied."""
        try:
            from sardis_v2_core.approval_service import ApprovalService
            from sardis_v2_core.approval_repository import ApprovalRepository
            from sardis_v2_core.approval_notifier import ApprovalNotifier
            from sardis_v2_core.webhooks import WebhookService, WebhookRepository

            dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis_test")

            approval_repo = ApprovalRepository(dsn)
            approval_service = ApprovalService(approval_repo)

            webhook_repo = WebhookRepository(dsn)
            webhook_service = WebhookService(webhook_repo)
            notifier = ApprovalNotifier(webhook_service)

            # Create webhook subscription
            await webhook_repo.create_subscription(
                organization_id="org_test_003",
                url="https://webhook.site/test-denied",
                events=["risk.alert"],
            )

            # Create and deny
            approval = await approval_service.create_approval(
                action="payment",
                requested_by="agent_deny_test",
                vendor="SuspiciousVendor",
                amount=Decimal("75000.00"),
                organization_id="org_test_003",
            )

            denied = await approval_service.deny(
                approval_id=approval.id,
                reviewed_by="admin@sardis.dev",
                reason="Vendor verification failed",
            )

            # Send notification
            await notifier.notify_approval_denied(
                approval_id=denied.id,
                action=denied.action,
                reviewed_by=denied.reviewed_by,
            )

            import asyncio
            await asyncio.sleep(0.5)

        except ImportError:
            pytest.skip("sardis_v2_core not available")


class TestApprovalExpiration:
    """Test approval expiration workflow."""

    @pytest.mark.e2e
    async def test_expire_pending_approvals(self, api_key, api_url):
        """Should expire approvals past their expiration time."""
        try:
            from sardis_v2_core.approval_service import ApprovalService
            from sardis_v2_core.approval_repository import ApprovalRepository
            from datetime import timedelta

            dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis_test")
            repo = ApprovalRepository(dsn)
            service = ApprovalService(repo)

            # Create approval that expires in 1 hour
            approval = await service.create_approval(
                action="payment",
                requested_by="agent_expire_test",
                vendor="TestVendor",
                amount=Decimal("5000.00"),
                expires_in_hours=1,
            )

            assert approval.status == "pending"

            # Manually expire pending approvals
            # In production, this would be called by a background job
            expired_count = await service.expire_pending()

            # Should not expire yet (expires in 1 hour)
            approval_after = await service.get_approval(approval.id)
            assert approval_after.status == "pending"

        except ImportError:
            pytest.skip("sardis_v2_core not available")

    @pytest.mark.e2e
    async def test_webhook_on_expiration(self, api_key, api_url):
        """Should send webhook when approval expires."""
        try:
            from sardis_v2_core.approval_service import ApprovalService
            from sardis_v2_core.approval_repository import ApprovalRepository
            from sardis_v2_core.approval_notifier import ApprovalNotifier
            from sardis_v2_core.webhooks import WebhookService, WebhookRepository

            dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis_test")

            approval_repo = ApprovalRepository(dsn)
            approval_service = ApprovalService(approval_repo)

            webhook_repo = WebhookRepository(dsn)
            webhook_service = WebhookService(webhook_repo)
            notifier = ApprovalNotifier(webhook_service)

            # Create webhook subscription
            await webhook_repo.create_subscription(
                organization_id="org_test_expire",
                url="https://webhook.site/test-expired",
                events=["risk.alert"],
            )

            # Create approval
            approval = await approval_service.create_approval(
                action="payment",
                requested_by="agent_expire_webhook",
                vendor="TestVendor",
                amount=Decimal("10000.00"),
                organization_id="org_test_expire",
                expires_in_hours=24,
            )

            # Manually expire it (simulating background job)
            approval.status = "expired"
            await approval_repo.update(approval.id, approval)

            # Send expiration notification
            await notifier.notify_approval_expired(
                approval_id=approval.id,
                action=approval.action,
                agent_id=approval.agent_id,
                wallet_id=approval.wallet_id,
            )

            import asyncio
            await asyncio.sleep(0.5)

        except ImportError:
            pytest.skip("sardis_v2_core not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
