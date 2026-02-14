"""Narrowed execution MVP endpoints (TAP issuance, AP2 validation, Base Sepolia USDC execution)."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, replace
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_protocol.verifier import MandateVerifier
from sardis_chain.executor import ChainExecutor
from sardis_ledger.records import LedgerStore
from sardis_v2_core.identity import AgentIdentity, IdentityRegistry
from sardis_v2_core.mandates import PaymentMandate, VCProof
from sardis_v2_core import SardisSettings
from sardis_v2_core.transactions import validate_wallet_not_frozen
from sardis_v2_core.wallet_repository import WalletRepository

from sardis_api.authz import require_principal
from sardis_api.authz import Principal
from sardis_api.execution_mode import enforce_staging_live_guard, get_pilot_execution_policy
from sardis_v2_core import AgentRepository

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_principal)])
METRICS = {
    "mandate_validations": 0,
    "mandate_rejections": 0,
    "executions": 0,
    "execution_failures": 0,
}


# --- Request/Response models ---
class IssueIdentityRequest(BaseModel):
    domain: str = Field(..., description="Domain binding for the agent")
    algorithm: str = Field(default="ed25519", pattern="^(ed25519|ecdsa-p256)$")
    agent_id: Optional[str] = Field(default=None, description="Optional agent ID (hex-encoded pubkey). If omitted, generated.")
    seed: Optional[str] = Field(default=None, description="Optional hex seed for deterministic testing (do not use in prod).")


class IssueIdentityResponse(BaseModel):
    agent_id: str
    domain: str
    algorithm: str
    public_key: str
    verification_method: str
    fingerprint: str
    created_at: int
    version: int
    private_key: Optional[str] = Field(default=None, description="Sandbox-only hex private key (omitted if provided by caller).")


class MandatePayload(BaseModel):
    mandate: Dict[str, Any]


class MandateValidationResponse(BaseModel):
    mandate_id: str
    accepted: bool
    reason: Optional[str] = None
    policy: Dict[str, Any] = Field(default_factory=dict)


class ExecuteResponse(BaseModel):
    status: str
    tx_hash: str
    chain: str
    block_number: int
    receipt: Dict[str, Any]


# --- Dependencies ---
@dataclass
class Dependencies:
    verifier: MandateVerifier
    chain_executor: ChainExecutor
    ledger: LedgerStore
    identity_registry: IdentityRegistry
    settings: SardisSettings
    wallet_repo: WalletRepository
    agent_repo: AgentRepository


def get_deps() -> Dependencies:
    raise NotImplementedError("Dependency override required")


# --- Helpers ---
MAX_AMOUNT_MINOR = 1_000_000_000  # 1,000 USDC if 6 decimals
ALLOWED_CHAIN = "base_sepolia"
ALLOWED_TOKEN = "USDC"


def _parse_payment_mandate(data: Dict[str, Any]) -> PaymentMandate:
    try:
        proof = data.get("proof")
        if isinstance(proof, dict):
            data = {**data, "proof": VCProof(**proof)}
        return PaymentMandate(**data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"invalid_mandate_payload: {exc}") from exc


def _policy_check(mandate: PaymentMandate, settings: SardisSettings) -> tuple[bool, Optional[str]]:
    if mandate.chain != ALLOWED_CHAIN:
        return False, "unsupported_chain"
    if mandate.token != ALLOWED_TOKEN:
        return False, "unsupported_token"
    if mandate.amount_minor <= 0:
        return False, "invalid_amount"
    if mandate.amount_minor > MAX_AMOUNT_MINOR:
        return False, "amount_exceeds_limit"
    now = int(time.time())
    if mandate.expires_at <= now:
        return False, "mandate_expired"
    # Enforce TTL upper bound to reduce replay window
    if mandate.expires_at - now > settings.mandate_ttl_seconds:
        return False, "ttl_too_long"
    return True, None


# --- Endpoints ---
@router.post("/tap/issue", response_model=IssueIdentityResponse, status_code=status.HTTP_201_CREATED)
def issue_identity(payload: IssueIdentityRequest, deps: Dependencies = Depends(get_deps)):
    """Issue a TAP identity with domain binding. In-memory for MVP."""
    if payload.algorithm not in {"ed25519", "ecdsa-p256"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="unsupported_algorithm")

    if payload.agent_id:
        # Provided public key (hex)
        try:
            public_key = bytes.fromhex(payload.agent_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="agent_id_not_hex") from exc
        identity = AgentIdentity(
            agent_id=payload.agent_id,
            public_key=public_key,
            algorithm=payload.algorithm,  # type: ignore[arg-type]
            domain=payload.domain,
        )
        secret = None
    else:
        seed_bytes = bytes.fromhex(payload.seed) if payload.seed else None
        identity, secret = AgentIdentity.generate(seed=seed_bytes)
        # secret is the private key (only for sandbox)

    record = deps.identity_registry.issue(
        agent_id=identity.agent_id,
        public_key=identity.public_key,
        domain=payload.domain,
        algorithm=identity.algorithm,  # type: ignore[arg-type]
    )

    return IssueIdentityResponse(
        agent_id=record.agent_id,
        domain=record.domain,
        algorithm=record.algorithm,
        public_key=record.public_key.hex(),
        verification_method=record.verification_method,
        fingerprint=record.fingerprint,
        created_at=record.created_at,
        version=record.version,
        private_key=secret.hex() if secret else None,
    )


@router.post("/mandates/validate", response_model=MandateValidationResponse)
def validate_mandate(payload: MandatePayload, deps: Dependencies = Depends(get_deps)):
    """Validate AP2 payment mandate: signature, domain binding, replay, TTL, policy."""
    mandate = _parse_payment_mandate(payload.mandate)

    policy_ok, policy_reason = _policy_check(mandate, deps.settings)
    verification = deps.verifier.verify(mandate)

    if not verification.accepted:
        METRICS["mandate_rejections"] += 1
        logger.warning("mandate_rejected signature=%s policy=%s mandate=%s", verification.reason, policy_reason, mandate.mandate_id)
        return MandateValidationResponse(
            mandate_id=mandate.mandate_id,
            accepted=False,
            reason=verification.reason,
            policy={"allowed": policy_ok, "reason": policy_reason},
        )

    if not policy_ok:
        METRICS["mandate_rejections"] += 1
        logger.warning("mandate_policy_block reason=%s mandate=%s", policy_reason, mandate.mandate_id)
        return MandateValidationResponse(
            mandate_id=mandate.mandate_id,
            accepted=False,
            reason=policy_reason,
            policy={"allowed": False, "reason": policy_reason},
        )

    METRICS["mandate_validations"] += 1
    logger.info("mandate_accepted mandate=%s", mandate.mandate_id)
    return MandateValidationResponse(
        mandate_id=mandate.mandate_id,
        accepted=True,
        reason=None,
        policy={"allowed": True},
    )


@router.post("/payments/execute", response_model=ExecuteResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_payment(
    payload: MandatePayload,
    deps: Dependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Validate + execute a single-rail Base Sepolia USDC payment.
    Requires SARDIS_CHAIN_MODE=live and SARDIS_EOA_PRIVATE_KEY configured.
    """
    if deps.settings.chain_mode == "simulated":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="chain_mode_simulated_set_live_for_execution",
        )

    mandate = _parse_payment_mandate(payload.mandate)
    policy_ok, policy_reason = _policy_check(mandate, deps.settings)
    verification = deps.verifier.verify(mandate)

    if not verification.accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=verification.reason or "mandate_invalid")
    if not policy_ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=policy_reason or "policy_violation")

    agent = await deps.agent_repo.get(mandate.subject)
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="agent_not_found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="access_denied")

    wallet = await deps.wallet_repo.get_by_agent(mandate.subject)
    if not wallet:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="wallet_not_found_for_agent")
    pilot_policy = get_pilot_execution_policy(deps.settings)
    enforce_staging_live_guard(
        policy=pilot_policy,
        principal=principal,
        merchant_domain=getattr(mandate, "merchant_domain", None),
        amount=None,
        operation="mvp.payments.execute",
    )
    freeze_ok, freeze_reason = validate_wallet_not_frozen(wallet)
    if not freeze_ok:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=freeze_reason)
    mandate = replace(mandate, wallet_id=wallet.wallet_id)

    try:
        chain_receipt = await deps.chain_executor.dispatch_payment(mandate)
    except Exception as exc:  # noqa: BLE001
        logger.exception("execution_failed")
        METRICS["execution_failures"] += 1
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Ledger + deterministic receipt
    deps.ledger.append(payment_mandate=mandate, chain_receipt=chain_receipt)
    receipt = deps.ledger.create_receipt(payment_mandate=mandate, chain_receipt=chain_receipt)

    logger.info(
        "payment_executed mandate=%s tx=%s chain=%s receipt=%s",
        mandate.mandate_id,
        chain_receipt.tx_hash,
        chain_receipt.chain,
        receipt["receipt_id"],
    )
    METRICS["executions"] += 1

    return ExecuteResponse(
        status="executed",
        tx_hash=chain_receipt.tx_hash,
        chain=chain_receipt.chain,
        block_number=chain_receipt.block_number or 0,
        receipt=receipt,
    )


@router.get("/receipts/{receipt_id}")
def get_receipt(receipt_id: str, deps: Dependencies = Depends(get_deps)):
    receipt = deps.ledger.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="receipt_not_found")
    return receipt


@router.get("/metrics")
def metrics(deps: Dependencies = Depends(get_deps)):
    """Lightweight counters + safety limits for MVP."""
    return {
        "metrics": METRICS,
        "limits": {
            "max_amount_minor": MAX_AMOUNT_MINOR,
            "ttl_seconds": deps.settings.mandate_ttl_seconds,
            "chain": ALLOWED_CHAIN,
            "token": ALLOWED_TOKEN,
        },
    }
