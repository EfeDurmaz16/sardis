"""Typed protocol payloads for the API service."""
from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from sardis_v2_core.mandates import PaymentMandate


class IngestMandateRequest(BaseModel):
    mandate: PaymentMandate
    attestation_bundle: dict = Field(
        default_factory=dict,
        description="VC/VP bundle containing chain-of-custody data",
    )


class MandateExecutionResponse(BaseModel):
    mandate_id: str
    status: str
    tx_hash: str
    chain: str
    audit_anchor: str


class AP2PaymentExecuteRequest(BaseModel):
    intent: Dict[str, Any]
    cart: Dict[str, Any]
    payment: Dict[str, Any]


class AP2PaymentExecuteResponse(BaseModel):
    mandate_id: str
    ledger_tx_id: str
    chain_tx_hash: str
    chain: str
    audit_anchor: str
    status: str
    compliance_provider: str | None = None
    compliance_rule: str | None = None
