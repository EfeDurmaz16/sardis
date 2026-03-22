"""Tests for MPP (Machine Payments Protocol) API endpoints."""
from decimal import Decimal

from sardis_v2_core.mpp import MPPPayment, MPPPaymentStatus, MPPSession, MPPSessionStatus


class TestMPPSessionModel:
    """Verify MPP session model behavior."""

    def test_session_defaults(self):
        session = MPPSession()
        assert session.status == MPPSessionStatus.ACTIVE
        assert session.method == "tempo"
        assert session.chain == "tempo"
        assert session.currency == "USDC"
        assert session.payment_count == 0

    def test_session_id_prefix(self):
        session = MPPSession()
        assert session.session_id.startswith("mpp_sess_")

    def test_can_spend_within_limit(self):
        session = MPPSession(spending_limit=Decimal("100"), remaining=Decimal("100"))
        assert session.can_spend(Decimal("50")) is True

    def test_cannot_spend_over_limit(self):
        session = MPPSession(spending_limit=Decimal("100"), remaining=Decimal("30"))
        assert session.can_spend(Decimal("50")) is False

    def test_cannot_spend_when_closed(self):
        session = MPPSession(
            spending_limit=Decimal("100"),
            remaining=Decimal("100"),
            status=MPPSessionStatus.CLOSED,
        )
        assert session.can_spend(Decimal("10")) is False

    def test_record_payment_updates_remaining(self):
        session = MPPSession(spending_limit=Decimal("100"), remaining=Decimal("100"))
        session.record_payment(Decimal("40"))
        assert session.remaining == Decimal("60")
        assert session.total_spent == Decimal("40")
        assert session.payment_count == 1

    def test_record_payment_exhausts_session(self):
        session = MPPSession(spending_limit=Decimal("100"), remaining=Decimal("100"))
        session.record_payment(Decimal("100"))
        assert session.status == MPPSessionStatus.EXHAUSTED

    def test_close_session(self):
        session = MPPSession()
        session.close()
        assert session.status == MPPSessionStatus.CLOSED
        assert session.closed_at is not None


class TestMPPPaymentModel:
    """Verify MPP payment model."""

    def test_payment_defaults(self):
        payment = MPPPayment()
        assert payment.status == MPPPaymentStatus.PENDING
        assert payment.chain == "tempo"
        assert payment.tx_hash is None

    def test_payment_id_prefix(self):
        payment = MPPPayment()
        assert payment.payment_id.startswith("mpp_pay_")


class TestMPPRouterImport:
    """Verify MPP router can be imported."""

    def test_router_import(self):
        from sardis_api.routers.mpp import router
        assert router is not None

    def test_router_has_endpoints(self):
        from sardis_api.routers.mpp import router
        paths = [r.path for r in router.routes]
        assert "/sessions" in paths
        assert "/sessions/{session_id}" in paths
        assert "/sessions/{session_id}/execute" in paths
        assert "/sessions/{session_id}/close" in paths
        assert "/evaluate" in paths
        assert "/simulate" in paths
