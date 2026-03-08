"""Delegated execution adapter — ControlPlane ChainExecutor implementation.

Loads credential from store, validates scope, calls DelegatedExecutorPort.
"""
from __future__ import annotations

import logging
from typing import Any

from sardis_v2_core.credential_store import CredentialStore
from sardis_v2_core.delegated_credential import CredentialStatus
from sardis_v2_core.delegated_executor import (
    DelegatedExecutorPort,
    DelegatedPaymentRequest,
)
from sardis_v2_core.execution_intent import ExecutionIntent

logger = logging.getLogger(__name__)


class DelegatedExecutionAdapter:
    """Adapts DelegatedExecutorPort to the ControlPlane ChainExecutor interface."""

    def __init__(
        self,
        executor_port: DelegatedExecutorPort,
        credential_store: CredentialStore,
    ) -> None:
        self._executor = executor_port
        self._cred_store = credential_store

    async def execute(self, intent: ExecutionIntent) -> dict[str, Any]:
        cred_id = intent.credential_id or intent.metadata.get("credential_id", "")
        if not cred_id:
            raise RuntimeError("No credential_id on intent for delegated execution")

        credential = await self._cred_store.get(cred_id)
        if credential is None:
            raise RuntimeError(f"Credential {cred_id} not found")

        if credential.status != CredentialStatus.ACTIVE:
            raise RuntimeError(
                f"Credential {cred_id} not active ({credential.status.value})"
            )

        ok, reason = credential.can_execute(
            intent.amount,
            merchant_id=intent.metadata.get("merchant_id"),
            mcc_code=intent.metadata.get("mcc_code"),
        )
        if not ok:
            raise RuntimeError(f"Credential scope check failed: {reason}")

        request = DelegatedPaymentRequest(
            credential_reference=credential.token_reference,
            consent_reference=credential.consent_id or "",
            merchant_binding=intent.metadata.get("merchant_id", ""),
            usage_scope=credential.scope,
            amount=intent.amount,
            currency=intent.currency,
            idempotency_key=intent.idempotency_key or intent.intent_id,
            metadata=intent.metadata,
        )

        result = await self._executor.execute(request, credential)

        if not result.success:
            raise RuntimeError(
                f"Delegated execution failed: {result.error}"
            )

        return {
            "tx_hash": result.reference_id,
            "status": result.settlement_status,
            "execution_mode": "delegated_card",
            "network": result.network,
            "fee": str(result.fee),
            "authorization_id": result.authorization_id,
        }
