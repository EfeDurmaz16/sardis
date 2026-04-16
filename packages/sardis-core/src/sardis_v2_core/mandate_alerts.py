"""Mandate alert service — budget and deadline notifications.

Checks mandates for budget thresholds and approaching deadlines,
then delivers webhooks to the principal/organization.

Usage:
    alert_service = MandateAlertService(mandate_repo, webhook_service)
    alerts = await alert_service.check_and_alert()
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

logger = logging.getLogger("sardis.mandate_alerts")


@dataclass(frozen=True)
class MandateAlert:
    """An alert generated for a spending mandate."""
    mandate_id: str
    alert_type: str  # budget_warning | budget_critical | deadline_warning | deadline_expired
    message: str
    threshold_pct: int | None = None
    remaining: Decimal | None = None
    deadline: datetime | None = None


# Budget thresholds (percentage of total spent)
BUDGET_WARNING_PCT = 80
BUDGET_CRITICAL_PCT = 95

# Deadline warning window
DEADLINE_WARNING_HOURS = 24


class MandateAlertService:
    """Checks mandates for budget and deadline conditions, sends alerts."""

    def __init__(
        self,
        mandate_repo: Any,
        notification_service: Any | None = None,
    ) -> None:
        self._mandate_repo = mandate_repo
        self._notifier = notification_service

    async def check_mandate(self, mandate: Any) -> list[MandateAlert]:
        """Check a single mandate for alertable conditions."""
        alerts: list[MandateAlert] = []

        # Budget alerts
        if mandate.amount_total and mandate.amount_total > 0:
            spent_pct = int((mandate.spent_total / mandate.amount_total) * 100)
            remaining = mandate.amount_total - mandate.spent_total

            if spent_pct >= BUDGET_CRITICAL_PCT:
                alerts.append(MandateAlert(
                    mandate_id=mandate.id,
                    alert_type="budget_critical",
                    message=f"Mandate {mandate.id} is at {spent_pct}% budget usage. "
                            f"Remaining: ${remaining:.2f} of ${mandate.amount_total:.2f}",
                    threshold_pct=spent_pct,
                    remaining=remaining,
                ))
            elif spent_pct >= BUDGET_WARNING_PCT:
                alerts.append(MandateAlert(
                    mandate_id=mandate.id,
                    alert_type="budget_warning",
                    message=f"Mandate {mandate.id} has used {spent_pct}% of budget. "
                            f"Remaining: ${remaining:.2f} of ${mandate.amount_total:.2f}",
                    threshold_pct=spent_pct,
                    remaining=remaining,
                ))

        # Deadline alerts
        if mandate.expires_at:
            now = datetime.now(UTC)
            if mandate.expires_at <= now:
                alerts.append(MandateAlert(
                    mandate_id=mandate.id,
                    alert_type="deadline_expired",
                    message=f"Mandate {mandate.id} has expired (was {mandate.expires_at.isoformat()})",
                    deadline=mandate.expires_at,
                ))
            elif mandate.expires_at <= now + timedelta(hours=DEADLINE_WARNING_HOURS):
                hours_left = (mandate.expires_at - now).total_seconds() / 3600
                alerts.append(MandateAlert(
                    mandate_id=mandate.id,
                    alert_type="deadline_warning",
                    message=f"Mandate {mandate.id} expires in {hours_left:.1f} hours",
                    deadline=mandate.expires_at,
                ))

        return alerts

    async def check_and_notify(self, mandate: Any) -> list[MandateAlert]:
        """Check mandate and send notifications for any alerts."""
        alerts = await self.check_mandate(mandate)

        if alerts and self._notifier:
            for alert in alerts:
                try:
                    await self._notifier.send(
                        principal_id=mandate.principal_id,
                        event_type=f"mandate.{alert.alert_type}",
                        payload={
                            "mandate_id": alert.mandate_id,
                            "alert_type": alert.alert_type,
                            "message": alert.message,
                            "threshold_pct": alert.threshold_pct,
                            "remaining": str(alert.remaining) if alert.remaining else None,
                            "deadline": alert.deadline.isoformat() if alert.deadline else None,
                        },
                    )
                except Exception:
                    logger.exception("Failed to send mandate alert for %s", alert.mandate_id)

        return alerts

    async def check_after_payment(
        self, mandate_id: str, payment_amount: Decimal
    ) -> list[MandateAlert]:
        """Quick check after a payment — only budget alerts.

        Call this from the checkout pay endpoint after incrementing spent_total.
        """
        mandate = await self._mandate_repo.get(mandate_id)
        if not mandate:
            return []

        alerts: list[MandateAlert] = []
        if mandate.amount_total and mandate.amount_total > 0:
            new_spent = mandate.spent_total + payment_amount
            spent_pct = int((new_spent / mandate.amount_total) * 100)
            remaining = mandate.amount_total - new_spent

            if spent_pct >= BUDGET_CRITICAL_PCT:
                alerts.append(MandateAlert(
                    mandate_id=mandate_id,
                    alert_type="budget_critical",
                    message=f"Mandate budget critical: {spent_pct}% used, ${remaining:.2f} remaining",
                    threshold_pct=spent_pct,
                    remaining=remaining,
                ))
            elif spent_pct >= BUDGET_WARNING_PCT:
                alerts.append(MandateAlert(
                    mandate_id=mandate_id,
                    alert_type="budget_warning",
                    message=f"Mandate budget warning: {spent_pct}% used, ${remaining:.2f} remaining",
                    threshold_pct=spent_pct,
                    remaining=remaining,
                ))

        return alerts
