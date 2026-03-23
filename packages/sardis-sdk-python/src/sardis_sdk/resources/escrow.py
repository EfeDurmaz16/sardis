"""
Escrow resource for Sardis SDK.

Sardis Protocol v1.0 -- Escrow holds, delivery confirmation, and dispute
resolution. Provides conditional payment holds tied to delivery milestones,
with a structured dispute flow supporting evidence submission and
resolution outcomes.

This module provides both async and sync interfaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from decimal import Decimal

    from ..client import TimeoutConfig


class AsyncEscrowResource(AsyncBaseResource):
    """Async resource for escrow operations.

    Escrow provides conditional payment holds with delivery confirmation
    and dispute resolution for agent-to-merchant transactions.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Create an escrow hold
            hold = await client.escrow.create_hold(
                payment_object_id="po_abc",
                merchant_id="merch_xyz",
                amount=Decimal("500.00"),
            )

            # Confirm delivery to release funds
            await client.escrow.confirm_delivery(
                hold_id=hold["id"],
                evidence={"tracking": "1Z999AA10123456784"},
            )

            # Or file a dispute
            dispute = await client.escrow.file_dispute(
                hold_id=hold["id"],
                reason="goods_not_received",
                description="Item never arrived",
            )
        ```
    """

    async def create_hold(
        self,
        payment_object_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        expiry_hours: int | None = None,
        conditions: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Create an escrow hold on a payment object.

        Args:
            payment_object_id: The payment object to escrow
            merchant_id: The merchant receiving funds upon delivery
            amount: Amount to hold in escrow
            currency: Currency code (default: USDC)
            expiry_hours: Hours until the hold auto-expires
            conditions: Optional delivery conditions to satisfy
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The created escrow hold
        """
        payload: dict[str, Any] = {
            "payment_object_id": payment_object_id,
            "merchant_id": merchant_id,
            "amount": str(amount),
            "currency": currency,
        }

        if expiry_hours is not None:
            payload["expiry_hours"] = expiry_hours
        if conditions is not None:
            payload["conditions"] = conditions
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._post("escrow/holds", payload, timeout=timeout)

    async def confirm_delivery(
        self,
        hold_id: str,
        evidence: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Confirm delivery to release escrowed funds to the merchant.

        Args:
            hold_id: The escrow hold ID
            evidence: Optional evidence of delivery (tracking info, signatures, etc.)
            timeout: Optional request timeout

        Returns:
            Confirmation result with settlement details
        """
        payload: dict[str, Any] = {}
        if evidence is not None:
            payload["evidence"] = evidence

        return await self._post(
            f"escrow/holds/{hold_id}/confirm", payload, timeout=timeout
        )

    async def file_dispute(
        self,
        hold_id: str,
        reason: str,
        description: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """File a dispute against an escrow hold.

        Args:
            hold_id: The escrow hold ID
            reason: Dispute reason code (e.g., "goods_not_received",
                "goods_damaged", "not_as_described", "unauthorized")
            description: Optional detailed description of the dispute
            timeout: Optional request timeout

        Returns:
            The created dispute
        """
        payload: dict[str, Any] = {
            "hold_id": hold_id,
            "reason": reason,
        }

        if description is not None:
            payload["description"] = description

        return await self._post("escrow/disputes", payload, timeout=timeout)

    async def submit_evidence(
        self,
        dispute_id: str,
        party: str,
        evidence_type: str,
        content: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Submit evidence for an ongoing dispute.

        Args:
            dispute_id: The dispute ID
            party: Which party is submitting ("payer" or "merchant")
            evidence_type: Type of evidence (e.g., "receipt", "tracking",
                "screenshot", "communication", "contract")
            content: Evidence content (text, URL, or base64-encoded data)
            timeout: Optional request timeout

        Returns:
            Evidence submission confirmation
        """
        payload: dict[str, Any] = {
            "party": party,
            "evidence_type": evidence_type,
            "content": content,
        }

        return await self._post(
            f"escrow/disputes/{dispute_id}/evidence", payload, timeout=timeout
        )

    async def resolve_dispute(
        self,
        dispute_id: str,
        outcome: str,
        payer_amount: Decimal | None = None,
        merchant_amount: Decimal | None = None,
        reasoning: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Resolve a dispute with a final outcome.

        Args:
            dispute_id: The dispute ID
            outcome: Resolution outcome ("payer_wins", "merchant_wins", "split")
            payer_amount: Amount returned to payer (for "split" outcome)
            merchant_amount: Amount released to merchant (for "split" outcome)
            reasoning: Optional reasoning for the resolution
            timeout: Optional request timeout

        Returns:
            Resolution result with settlement details
        """
        payload: dict[str, Any] = {
            "outcome": outcome,
        }

        if payer_amount is not None:
            payload["payer_amount"] = str(payer_amount)
        if merchant_amount is not None:
            payload["merchant_amount"] = str(merchant_amount)
        if reasoning is not None:
            payload["reasoning"] = reasoning

        return await self._post(
            f"escrow/disputes/{dispute_id}/resolve", payload, timeout=timeout
        )

    async def get_dispute(
        self,
        dispute_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a dispute by ID.

        Args:
            dispute_id: The dispute ID
            timeout: Optional request timeout

        Returns:
            The dispute object with current status and evidence
        """
        return await self._get(f"escrow/disputes/{dispute_id}", timeout=timeout)


class EscrowResource(SyncBaseResource):
    """Sync resource for escrow operations.

    Escrow provides conditional payment holds with delivery confirmation
    and dispute resolution for agent-to-merchant transactions.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Create an escrow hold
            hold = client.escrow.create_hold(
                payment_object_id="po_abc",
                merchant_id="merch_xyz",
                amount=Decimal("500.00"),
            )

            # Confirm delivery to release funds
            client.escrow.confirm_delivery(
                hold_id=hold["id"],
                evidence={"tracking": "1Z999AA10123456784"},
            )

            # Or file a dispute
            dispute = client.escrow.file_dispute(
                hold_id=hold["id"],
                reason="goods_not_received",
                description="Item never arrived",
            )
        ```
    """

    def create_hold(
        self,
        payment_object_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        expiry_hours: int | None = None,
        conditions: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Create an escrow hold on a payment object.

        Args:
            payment_object_id: The payment object to escrow
            merchant_id: The merchant receiving funds upon delivery
            amount: Amount to hold in escrow
            currency: Currency code (default: USDC)
            expiry_hours: Hours until the hold auto-expires
            conditions: Optional delivery conditions to satisfy
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The created escrow hold
        """
        payload: dict[str, Any] = {
            "payment_object_id": payment_object_id,
            "merchant_id": merchant_id,
            "amount": str(amount),
            "currency": currency,
        }

        if expiry_hours is not None:
            payload["expiry_hours"] = expiry_hours
        if conditions is not None:
            payload["conditions"] = conditions
        if metadata is not None:
            payload["metadata"] = metadata

        return self._post("escrow/holds", payload, timeout=timeout)

    def confirm_delivery(
        self,
        hold_id: str,
        evidence: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Confirm delivery to release escrowed funds to the merchant.

        Args:
            hold_id: The escrow hold ID
            evidence: Optional evidence of delivery (tracking info, signatures, etc.)
            timeout: Optional request timeout

        Returns:
            Confirmation result with settlement details
        """
        payload: dict[str, Any] = {}
        if evidence is not None:
            payload["evidence"] = evidence

        return self._post(
            f"escrow/holds/{hold_id}/confirm", payload, timeout=timeout
        )

    def file_dispute(
        self,
        hold_id: str,
        reason: str,
        description: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """File a dispute against an escrow hold.

        Args:
            hold_id: The escrow hold ID
            reason: Dispute reason code (e.g., "goods_not_received",
                "goods_damaged", "not_as_described", "unauthorized")
            description: Optional detailed description of the dispute
            timeout: Optional request timeout

        Returns:
            The created dispute
        """
        payload: dict[str, Any] = {
            "hold_id": hold_id,
            "reason": reason,
        }

        if description is not None:
            payload["description"] = description

        return self._post("escrow/disputes", payload, timeout=timeout)

    def submit_evidence(
        self,
        dispute_id: str,
        party: str,
        evidence_type: str,
        content: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Submit evidence for an ongoing dispute.

        Args:
            dispute_id: The dispute ID
            party: Which party is submitting ("payer" or "merchant")
            evidence_type: Type of evidence (e.g., "receipt", "tracking",
                "screenshot", "communication", "contract")
            content: Evidence content (text, URL, or base64-encoded data)
            timeout: Optional request timeout

        Returns:
            Evidence submission confirmation
        """
        payload: dict[str, Any] = {
            "party": party,
            "evidence_type": evidence_type,
            "content": content,
        }

        return self._post(
            f"escrow/disputes/{dispute_id}/evidence", payload, timeout=timeout
        )

    def resolve_dispute(
        self,
        dispute_id: str,
        outcome: str,
        payer_amount: Decimal | None = None,
        merchant_amount: Decimal | None = None,
        reasoning: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Resolve a dispute with a final outcome.

        Args:
            dispute_id: The dispute ID
            outcome: Resolution outcome ("payer_wins", "merchant_wins", "split")
            payer_amount: Amount returned to payer (for "split" outcome)
            merchant_amount: Amount released to merchant (for "split" outcome)
            reasoning: Optional reasoning for the resolution
            timeout: Optional request timeout

        Returns:
            Resolution result with settlement details
        """
        payload: dict[str, Any] = {
            "outcome": outcome,
        }

        if payer_amount is not None:
            payload["payer_amount"] = str(payer_amount)
        if merchant_amount is not None:
            payload["merchant_amount"] = str(merchant_amount)
        if reasoning is not None:
            payload["reasoning"] = reasoning

        return self._post(
            f"escrow/disputes/{dispute_id}/resolve", payload, timeout=timeout
        )

    def get_dispute(
        self,
        dispute_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a dispute by ID.

        Args:
            dispute_id: The dispute ID
            timeout: Optional request timeout

        Returns:
            The dispute object with current status and evidence
        """
        return self._get(f"escrow/disputes/{dispute_id}", timeout=timeout)


__all__ = [
    "AsyncEscrowResource",
    "EscrowResource",
]
