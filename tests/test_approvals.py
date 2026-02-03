"""Tests for approval service and repository."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from sardis_v2_core.approval_repository import (
    Approval,
    ApprovalRepository,
    ApprovalStatus,
    ApprovalUrgency,
)
from sardis_v2_core.approval_service import ApprovalService


class TestApprovalModel:
    """Test Approval dataclass."""

    def test_generate_id(self):
        """Test approval ID generation."""
        approval_id = Approval.generate_id()
        assert approval_id.startswith("appr_")
        assert len(approval_id.split("_")) == 3
        assert len(approval_id) > 10

    def test_generate_id_unique(self):
        """Test that generated IDs are unique."""
        id1 = Approval.generate_id()
        id2 = Approval.generate_id()
        assert id1 != id2

    def test_approval_creation(self):
        """Test creating an Approval object."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)

        approval = Approval(
            id="appr_test_123",
            action="payment",
            status="pending",
            urgency="medium",
            requested_by="agent_001",
            created_at=now,
            expires_at=expires,
            amount=Decimal("100.00"),
            vendor="test_vendor",
            purpose="Test payment",
        )

        assert approval.id == "appr_test_123"
        assert approval.action == "payment"
        assert approval.status == "pending"
        assert approval.urgency == "medium"
        assert approval.requested_by == "agent_001"
        assert approval.amount == Decimal("100.00")
        assert approval.vendor == "test_vendor"
        assert approval.purpose == "Test payment"


class TestApprovalRepository:
    """Test ApprovalRepository CRUD operations."""

    @pytest.fixture
    def mock_database(self):
        """Mock database for testing."""
        with patch("sardis_v2_core.approval_repository.Database") as mock_db:
            yield mock_db

    @pytest.fixture
    def repository(self):
        """Create repository instance."""
        return ApprovalRepository()

    @pytest.mark.anyio
    async def test_create_approval(self, repository, mock_database):
        """Test creating an approval."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)

        mock_database.execute = AsyncMock()

        result = await repository.create(
            action="payment",
            status="pending",
            urgency="high",
            requested_by="agent_001",
            created_at=now,
            expires_at=expires,
            amount=Decimal("500.00"),
            vendor="acme_corp",
            purpose="Emergency payment",
            reason="Exceeds daily limit",
        )

        assert result.action == "payment"
        assert result.status == "pending"
        assert result.requested_by == "agent_001"
        mock_database.execute.assert_called_once()

    @pytest.mark.anyio
    async def test_get_approval(self, repository, mock_database):
        """Test retrieving an approval by ID."""
        mock_row = {
            "id": "appr_test_002",
            "action": "create_card",
            "status": "approved",
            "urgency": "medium",
            "requested_by": "agent_002",
            "reviewed_by": "admin@example.com",
            "created_at": datetime.now(timezone.utc),
            "reviewed_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
            "vendor": None,
            "amount": None,
            "purpose": "New virtual card",
            "reason": "First card creation",
            "card_limit": Decimal("1000.00"),
            "agent_id": "agent_002",
            "wallet_id": "wallet_001",
            "organization_id": "org_001",
            "metadata": {},
        }

        mock_database.fetchrow = AsyncMock(return_value=mock_row)

        approval = await repository.get("appr_test_002")

        assert approval is not None
        assert approval.id == "appr_test_002"
        assert approval.action == "create_card"
        assert approval.status == "approved"
        assert approval.card_limit == Decimal("1000.00")

    @pytest.mark.anyio
    async def test_get_approval_not_found(self, repository, mock_database):
        """Test retrieving non-existent approval."""
        mock_database.fetchrow = AsyncMock(return_value=None)

        approval = await repository.get("appr_nonexistent")

        assert approval is None

    @pytest.mark.anyio
    async def test_update_approval(self, repository, mock_database):
        """Test updating an approval."""
        now = datetime.now(timezone.utc)

        mock_row = {
            "id": "appr_test_003",
            "action": "payment",
            "status": "approved",
            "urgency": "medium",
            "requested_by": "agent_003",
            "reviewed_by": "admin@example.com",
            "created_at": now,
            "reviewed_at": now,
            "expires_at": now + timedelta(hours=24),
            "vendor": None,
            "amount": None,
            "purpose": None,
            "reason": None,
            "card_limit": None,
            "agent_id": None,
            "wallet_id": None,
            "organization_id": None,
            "metadata": {"approved_reason": "Legitimate request"},
        }

        mock_database.fetchrow = AsyncMock(return_value=mock_row)

        updated = await repository.update(
            "appr_test_003",
            status="approved",
            reviewed_by="admin@example.com",
            reviewed_at=now,
            metadata={"approved_reason": "Legitimate request"},
        )

        assert updated is not None
        assert updated.status == "approved"
        assert updated.reviewed_by == "admin@example.com"

    @pytest.mark.anyio
    async def test_list_approvals(self, repository, mock_database):
        """Test listing approvals with filters."""
        now = datetime.now(timezone.utc)

        mock_rows = [
            {
                "id": f"appr_test_{i}",
                "action": "payment",
                "status": "pending",
                "urgency": "medium",
                "requested_by": "agent_001",
                "reviewed_by": None,
                "created_at": now,
                "reviewed_at": None,
                "expires_at": now + timedelta(hours=24),
                "vendor": None,
                "amount": Decimal("100.00"),
                "purpose": None,
                "reason": None,
                "card_limit": None,
                "agent_id": "agent_001",
                "wallet_id": None,
                "organization_id": None,
                "metadata": {},
            }
            for i in range(3)
        ]

        mock_database.fetch = AsyncMock(return_value=mock_rows)

        approvals = await repository.list(
            status="pending",
            agent_id="agent_001",
            limit=10,
        )

        assert len(approvals) == 3
        assert all(a.status == "pending" for a in approvals)

    @pytest.mark.anyio
    async def test_get_expired_pending(self, repository, mock_database):
        """Test retrieving expired pending approvals."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        mock_rows = [
            {
                "id": "appr_expired_001",
                "action": "payment",
                "status": "pending",
                "urgency": "low",
                "requested_by": "agent_001",
                "reviewed_by": None,
                "created_at": past - timedelta(days=1),
                "reviewed_at": None,
                "expires_at": past,
                "vendor": None,
                "amount": Decimal("50.00"),
                "purpose": None,
                "reason": None,
                "card_limit": None,
                "agent_id": None,
                "wallet_id": None,
                "organization_id": None,
                "metadata": {},
            }
        ]

        mock_database.fetch = AsyncMock(return_value=mock_rows)

        expired = await repository.get_expired_pending(as_of=now)

        assert len(expired) == 1
        assert expired[0].status == "pending"
        assert expired[0].expires_at < now


class TestApprovalService:
    """Test ApprovalService business logic."""

    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing."""
        return Mock(spec=ApprovalRepository)

    @pytest.fixture
    def service(self, mock_repository):
        """Create service instance with mock repository."""
        return ApprovalService(mock_repository)

    @pytest.mark.anyio
    async def test_create_approval(self, service, mock_repository):
        """Test creating an approval through service."""
        now = datetime.now(timezone.utc)

        created_approval = Approval(
            id="appr_new_001",
            action="payment",
            status="pending",
            urgency="high",
            requested_by="agent_001",
            created_at=now,
            expires_at=now + timedelta(hours=24),
            amount=Decimal("1000.00"),
            vendor="big_vendor",
            purpose="Large payment",
            reason="Exceeds limit",
        )

        mock_repository.create = AsyncMock(return_value=created_approval)

        approval = await service.create_approval(
            action="payment",
            requested_by="agent_001",
            amount=Decimal("1000.00"),
            vendor="big_vendor",
            purpose="Large payment",
            reason="Exceeds limit",
            urgency="high",
            expires_in_hours=24,
        )

        assert approval.id == "appr_new_001"
        assert approval.action == "payment"
        assert approval.urgency == "high"
        mock_repository.create.assert_called_once()

    @pytest.mark.anyio
    async def test_approve_approval(self, service, mock_repository):
        """Test approving a pending approval."""
        now = datetime.now(timezone.utc)

        pending_approval = Approval(
            id="appr_pending_001",
            action="payment",
            status="pending",
            urgency="medium",
            requested_by="agent_001",
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )

        approved_approval = Approval(
            id="appr_pending_001",
            action="payment",
            status="approved",
            urgency="medium",
            requested_by="agent_001",
            reviewed_by="admin@example.com",
            created_at=now,
            reviewed_at=now,
            expires_at=now + timedelta(hours=24),
        )

        mock_repository.get = AsyncMock(return_value=pending_approval)
        mock_repository.update = AsyncMock(return_value=approved_approval)

        result = await service.approve("appr_pending_001", "admin@example.com")

        assert result is not None
        assert result.status == "approved"
        assert result.reviewed_by == "admin@example.com"

    @pytest.mark.anyio
    async def test_approve_nonexistent(self, service, mock_repository):
        """Test approving non-existent approval."""
        mock_repository.get = AsyncMock(return_value=None)

        result = await service.approve("appr_nonexistent", "admin@example.com")

        assert result is None

    @pytest.mark.anyio
    async def test_approve_already_approved(self, service, mock_repository):
        """Test approving already approved approval."""
        now = datetime.now(timezone.utc)

        approved_approval = Approval(
            id="appr_already_001",
            action="payment",
            status="approved",
            urgency="medium",
            requested_by="agent_001",
            reviewed_by="admin1@example.com",
            created_at=now,
            reviewed_at=now,
            expires_at=now + timedelta(hours=24),
        )

        mock_repository.get = AsyncMock(return_value=approved_approval)

        result = await service.approve("appr_already_001", "admin2@example.com")

        assert result is None

    @pytest.mark.anyio
    async def test_deny_approval(self, service, mock_repository):
        """Test denying a pending approval."""
        now = datetime.now(timezone.utc)

        pending_approval = Approval(
            id="appr_pending_002",
            action="payment",
            status="pending",
            urgency="low",
            requested_by="agent_002",
            created_at=now,
            expires_at=now + timedelta(hours=24),
            metadata={},
        )

        denied_approval = Approval(
            id="appr_pending_002",
            action="payment",
            status="denied",
            urgency="low",
            requested_by="agent_002",
            reviewed_by="admin@example.com",
            created_at=now,
            reviewed_at=now,
            expires_at=now + timedelta(hours=24),
            metadata={"denial_reason": "Insufficient justification"},
        )

        mock_repository.get = AsyncMock(return_value=pending_approval)
        mock_repository.update = AsyncMock(return_value=denied_approval)

        result = await service.deny(
            "appr_pending_002",
            "admin@example.com",
            reason="Insufficient justification"
        )

        assert result is not None
        assert result.status == "denied"
        assert result.metadata["denial_reason"] == "Insufficient justification"

    @pytest.mark.anyio
    async def test_cancel_approval(self, service, mock_repository):
        """Test cancelling a pending approval."""
        now = datetime.now(timezone.utc)

        pending_approval = Approval(
            id="appr_pending_003",
            action="create_card",
            status="pending",
            urgency="medium",
            requested_by="agent_003",
            created_at=now,
            expires_at=now + timedelta(hours=24),
            metadata={},
        )

        cancelled_approval = Approval(
            id="appr_pending_003",
            action="create_card",
            status="cancelled",
            urgency="medium",
            requested_by="agent_003",
            created_at=now,
            expires_at=now + timedelta(hours=24),
            metadata={"cancellation_reason": "No longer needed"},
        )

        mock_repository.get = AsyncMock(return_value=pending_approval)
        mock_repository.update = AsyncMock(return_value=cancelled_approval)

        result = await service.cancel(
            "appr_pending_003",
            reason="No longer needed"
        )

        assert result is not None
        assert result.status == "cancelled"

    @pytest.mark.anyio
    async def test_expire_pending(self, service, mock_repository):
        """Test expiring pending approvals."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        expired_approvals = [
            Approval(
                id=f"appr_expired_{i}",
                action="payment",
                status="pending",
                urgency="low",
                requested_by="agent_001",
                created_at=past - timedelta(days=1),
                expires_at=past,
                metadata={},
            )
            for i in range(3)
        ]

        mock_repository.get_expired_pending = AsyncMock(return_value=expired_approvals)
        mock_repository.update = AsyncMock(side_effect=expired_approvals)

        count = await service.expire_pending()

        assert count == 3
        assert mock_repository.update.call_count == 3

    @pytest.mark.anyio
    async def test_list_pending(self, service, mock_repository):
        """Test listing pending approvals."""
        now = datetime.now(timezone.utc)

        pending_approvals = [
            Approval(
                id=f"appr_pending_{i}",
                action="payment",
                status="pending",
                urgency="medium",
                requested_by="agent_001",
                created_at=now,
                expires_at=now + timedelta(hours=24),
            )
            for i in range(5)
        ]

        mock_repository.list = AsyncMock(return_value=pending_approvals)

        approvals = await service.list_pending(urgency="medium", limit=10)

        assert len(approvals) == 5
        assert all(a.status == "pending" for a in approvals)
        mock_repository.list.assert_called_once_with(
            status="pending",
            agent_id=None,
            wallet_id=None,
            organization_id=None,
            requested_by=None,
            urgency="medium",
            limit=10,
            offset=0,
        )

    @pytest.mark.anyio
    async def test_get_approval(self, service, mock_repository):
        """Test getting approval by ID."""
        now = datetime.now(timezone.utc)

        approval = Approval(
            id="appr_get_001",
            action="payment",
            status="approved",
            urgency="high",
            requested_by="agent_001",
            reviewed_by="admin@example.com",
            created_at=now,
            reviewed_at=now,
            expires_at=now + timedelta(hours=24),
        )

        mock_repository.get = AsyncMock(return_value=approval)

        result = await service.get_approval("appr_get_001")

        assert result == approval
        mock_repository.get.assert_called_once_with("appr_get_001")
