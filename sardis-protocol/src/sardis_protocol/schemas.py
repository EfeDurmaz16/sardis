"""Typed protocol payloads for the API service."""
from __future__ import annotations

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
