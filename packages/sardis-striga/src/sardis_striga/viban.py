"""Striga vIBAN management — per-agent virtual IBANs for SEPA."""
from __future__ import annotations

import logging
from typing import Any

from .client import StrigaClient
from .models import StrigaTransaction, StrigaTransactionStatus, StrigaVIBAN, StrigaVIBANStatus

logger = logging.getLogger(__name__)


class StrigaVIBANManager:
    """
    Manages virtual IBANs via Striga API.

    Each agent wallet gets a dedicated vIBAN for receiving EUR via SEPA.
    """

    def __init__(self, client: StrigaClient):
        self._client = client

    async def create_viban(
        self,
        user_id: str,
        wallet_id: str,
        currency: str = "EUR",
    ) -> StrigaVIBAN:
        """
        Create a new vIBAN for an agent wallet.

        Args:
            user_id: Striga user ID (KYC-verified)
            wallet_id: Striga wallet ID to link
            currency: Currency for the vIBAN (default EUR)

        Returns:
            StrigaVIBAN with IBAN details
        """
        result = await self._client.request(
            "POST",
            "/wallets/viban",
            {
                "userId": user_id,
                "walletId": wallet_id,
                "currency": currency,
            },
        )

        return self._parse_viban(result)

    async def get_viban(self, viban_id: str) -> StrigaVIBAN | None:
        """Get vIBAN details by ID."""
        try:
            result = await self._client.request("GET", f"/wallets/viban/{viban_id}")
            return self._parse_viban(result)
        except Exception:
            return None

    async def get_viban_by_wallet(self, wallet_id: str) -> StrigaVIBAN | None:
        """Get vIBAN for a wallet."""
        try:
            result = await self._client.request(
                "GET", f"/wallets/{wallet_id}/viban"
            )
            return self._parse_viban(result)
        except Exception:
            return None

    async def list_transactions(
        self,
        viban_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StrigaTransaction]:
        """List SEPA transactions for a vIBAN."""
        result = await self._client.request(
            "GET",
            f"/wallets/viban/{viban_id}/transactions",
            params={"limit": limit, "offset": offset},
        )

        transactions = []
        for tx_data in result.get("transactions", []):
            transactions.append(self._parse_transaction(tx_data))
        return transactions

    def _parse_viban(self, data: dict[str, Any]) -> StrigaVIBAN:
        """Parse Striga vIBAN response."""
        status_map = {
            "active": StrigaVIBANStatus.ACTIVE,
            "blocked": StrigaVIBANStatus.BLOCKED,
            "closed": StrigaVIBANStatus.CLOSED,
        }

        return StrigaVIBAN(
            viban_id=data.get("vibanId", data.get("id", "")),
            wallet_id=data.get("walletId", ""),
            user_id=data.get("userId", ""),
            iban=data.get("iban", ""),
            bic=data.get("bic", ""),
            currency=data.get("currency", "EUR"),
            status=status_map.get(data.get("status", "active"), StrigaVIBANStatus.ACTIVE),
            bank_name=data.get("bankName", ""),
        )

    def _parse_transaction(self, data: dict[str, Any]) -> StrigaTransaction:
        """Parse Striga transaction for vIBAN."""
        from .models import StrigaTransactionType

        status_map = {
            "pending": StrigaTransactionStatus.PENDING,
            "processing": StrigaTransactionStatus.PROCESSING,
            "completed": StrigaTransactionStatus.COMPLETED,
            "failed": StrigaTransactionStatus.FAILED,
        }

        return StrigaTransaction(
            transaction_id=data.get("transactionId", ""),
            wallet_id=data.get("walletId", ""),
            transaction_type=StrigaTransactionType.SEPA_IN,
            status=status_map.get(data.get("status", "pending"), StrigaTransactionStatus.PENDING),
            amount_cents=int(data.get("amount", 0)),
            currency=data.get("currency", "EUR"),
            fee_cents=int(data.get("fee", 0)),
            description=data.get("description", ""),
            reference=data.get("reference"),
        )
