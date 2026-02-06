"""Typed protocol payloads for the API service."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from sardis_v2_core.mandates import PaymentMandate


# AP2 Protocol Version Constants
AP2_PROTOCOL_VERSION = "2025.1"
AP2_SUPPORTED_VERSIONS = ["2025.0", "2025.1"]


class IngestMandateRequest(BaseModel):
    """Request to ingest and execute a mandate."""
    mandate: PaymentMandate
    attestation_bundle: dict = Field(
        default_factory=dict,
        description="VC/VP bundle containing chain-of-custody data",
    )
    payment_method: str = Field(
        default="stablecoin",
        description="Payment method: stablecoin, virtual_card, x402, bank_transfer",
    )


class MandateExecutionResponse(BaseModel):
    """Response from mandate execution."""
    mandate_id: str
    status: str
    tx_hash: str
    chain: str
    audit_anchor: str
    payment_method: str = "stablecoin"


class AP2PaymentExecuteRequest(BaseModel):
    """
    AP2 payment execution request with Intent+Cart+Payment bundle.

    Supports multiple payment methods as per AP2's payment-agnostic design.
    """
    intent: Dict[str, Any]
    cart: Dict[str, Any]
    payment: Dict[str, Any]
    payment_method: str = Field(
        default="stablecoin",
        description="Payment method: stablecoin, virtual_card, x402, bank_transfer",
    )
    ap2_version: str | None = Field(
        default=None,
        description="AP2 protocol version (format: YYYY.MINOR, e.g. '2025.1')",
    )
    canonicalization_mode: str = Field(
        default="pipe",
        description="Canonicalization mode: pipe or jcs",
    )

    @field_validator("ap2_version")
    @classmethod
    def validate_ap2_version(cls, v: str | None) -> str | None:
        if v is None:
            return v
        import re
        if not re.match(r"^\d{4}\.\d+$", v):
            raise ValueError(f"Invalid AP2 version format: {v}. Expected YYYY.MINOR (e.g., '2025.1')")
        return v


class AP2PaymentExecuteResponse(BaseModel):
    """Response from AP2 payment execution."""
    mandate_id: str
    ledger_tx_id: str
    chain_tx_hash: str
    chain: str
    audit_anchor: str
    status: str
    payment_method: str = "stablecoin"
    compliance_provider: str | None = None
    compliance_rule: str | None = None


class X402PaymentExecuteRequest(BaseModel):
    """
    x402 micropayment execution request.
    
    Reference: https://www.x402.org/
    See also: https://github.com/google-agentic-commerce/a2a-x402
    """
    payment_id: str = Field(description="Unique payment identifier")
    payment_type: str = Field(
        default="per_request",
        description="Payment type: per_request, streaming, budget",
    )
    amount: str = Field(description="Amount in smallest unit (e.g., cents)")
    currency: str = Field(default="USD", description="Currency code")
    resource_uri: str = Field(description="URI of resource being paid for")
    resource_type: str = Field(
        default="api_call",
        description="Type of resource: api_call, data_access, etc.",
    )
    payer_address: str = Field(description="Payer's wallet or card address")
    payer_signature: str = Field(description="Cryptographic signature from payer")
    payee_address: str = Field(description="Payee's wallet address")
    x402_version: str = Field(default="1.0", description="x402 protocol version")
    x402_network: str = Field(default="base", description="Settlement network")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class X402PaymentExecuteResponse(BaseModel):
    """Response from x402 payment execution."""
    payment_id: str
    status: str  # pending, completed, failed
    tx_hash: Optional[str] = None
    chain: str = "base"
    access_token: Optional[str] = None
    expires_at: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
