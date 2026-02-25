"""Agent-to-Agent (A2A) payment endpoints.

Enables first-class agent-to-agent transfers:
- POST /pay          — Direct agent-to-agent payment by agent IDs
- POST /messages     — Inbound A2A message handler (payment requests, etc.)
- GET  /agent-card   — Sardis agent card for discovery
"""
from __future__ import annotations

import base64
import hashlib
from inspect import isawaitable
import json
import logging
import os
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from sardis_v2_core import AgentRepository, WalletRepository
from sardis_v2_core.identity import AgentIdentity, IdentityRegistry
from sardis_v2_core.tokens import TokenType, to_raw_token_amount
from sardis_v2_core.mandates import PaymentMandate, VCProof
from sardis_chain.executor import ChainExecutor
from sardis_ledger.records import LedgerStore
from sardis_api.authz import Principal, require_principal
from sardis_api.idempotency import get_idempotency_key, run_idempotent
from sardis_api.webhook_replay import run_with_replay_protection
from sardis_compliance.checks import ComplianceAuditEntry

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])

# Public router for unauthenticated endpoints (agent card)
public_router = APIRouter()

# Cross-org A2A should stay disabled unless explicitly opted in.
def _allow_cross_org_a2a() -> bool:
    raw = os.getenv("SARDIS_A2A_ALLOW_CROSS_ORG", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_production_env() -> bool:
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    return env in {"prod", "production"}


def _a2a_signature_required() -> bool:
    configured = os.getenv("SARDIS_A2A_REQUIRE_SIGNATURE", "").strip()
    if configured:
        return _is_truthy(configured)
    return _is_production_env()


def _allow_unsigned_a2a_dev() -> bool:
    configured = os.getenv("SARDIS_A2A_ALLOW_UNSIGNED_DEV", "1").strip()
    return _is_truthy(configured)


def _enforce_a2a_trust_table() -> bool:
    configured = os.getenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "").strip()
    if configured:
        return _is_truthy(configured)
    return _is_production_env()


def _parse_a2a_trust_table() -> dict[str, set[str]]:
    """
    Parse trust relations from env.

    Format:
      SARDIS_A2A_TRUST_RELATIONS="agent_a>agent_b|agent_c,agent_b>agent_a,*>agent_ops"
    """
    raw = os.getenv("SARDIS_A2A_TRUST_RELATIONS", "")
    table: dict[str, set[str]] = {}
    for item in raw.split(","):
        relation = item.strip()
        if not relation or ">" not in relation:
            continue
        sender, recipients = relation.split(">", 1)
        sender_key = sender.strip()
        if not sender_key:
            continue
        targets = {part.strip() for part in recipients.split("|") if part.strip()}
        if not targets:
            continue
        table.setdefault(sender_key, set()).update(targets)
    return table


def _trust_table_hash(table: dict[str, set[str]]) -> str:
    canonical = {
        str(sender): sorted(str(recipient) for recipient in recipients)
        for sender, recipients in sorted(table.items())
    }
    return hashlib.sha256(
        json.dumps(canonical, separators=(",", ":"), sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()


def _evaluate_trust_table(
    *,
    sender_agent_id: str,
    recipient_agent_id: str,
    table: dict[str, set[str]],
) -> tuple[bool, str]:
    if sender_agent_id == recipient_agent_id:
        return True, "self_trusted"
    if not table:
        return False, "a2a_trust_table_not_configured"
    sender_targets = table.get(sender_agent_id, set())
    wildcard_targets = table.get("*", set())
    if "*" in sender_targets or recipient_agent_id in sender_targets:
        return True, "trusted_sender_relation"
    if "*" in wildcard_targets or recipient_agent_id in wildcard_targets:
        return True, "trusted_wildcard_relation"
    return False, "a2a_agent_not_trusted"


def _check_a2a_trust_relation(sender_agent_id: str, recipient_agent_id: str) -> tuple[bool, str]:
    if not _enforce_a2a_trust_table():
        return True, "trust_table_not_enforced"
    return _evaluate_trust_table(
        sender_agent_id=sender_agent_id,
        recipient_agent_id=recipient_agent_id,
        table=_parse_a2a_trust_table(),
    )


async def _resolve_a2a_trust_table(
    *,
    deps: "A2ADependencies",
    organization_id: str,
) -> tuple[dict[str, set[str]], str]:
    repo = getattr(deps, "trust_repo", None)
    if repo is not None and hasattr(repo, "get_trust_table"):
        try:
            table = await repo.get_trust_table(organization_id)
            if table:
                normalized = {
                    str(sender): {str(recipient) for recipient in recipients}
                    for sender, recipients in table.items()
                }
                return normalized, "repository"
        except Exception:
            logger.exception("A2A trust repository unavailable for org=%s", organization_id)
            if _is_production_env():
                return {}, "repository_error"
    env_table = _parse_a2a_trust_table()
    if env_table:
        return env_table, "env"
    return {}, "none"


async def _check_a2a_trust_relation_with_deps(
    *,
    deps: "A2ADependencies",
    organization_id: str,
    sender_agent_id: str,
    recipient_agent_id: str,
) -> tuple[bool, str, str]:
    if not _enforce_a2a_trust_table():
        return True, "trust_table_not_enforced", "disabled"
    table, source = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=organization_id,
    )
    if source == "repository_error":
        return False, "a2a_trust_repository_unavailable", "repository"
    allowed, reason = _evaluate_trust_table(
        sender_agent_id=sender_agent_id,
        recipient_agent_id=recipient_agent_id,
        table=table,
    )
    if not table:
        return False, reason, source
    return allowed, reason, source


async def _append_a2a_trust_audit_entry(
    *,
    deps: "A2ADependencies",
    organization_id: str,
    actor_org_id: str,
    action: str,
    sender_agent_id: str,
    recipient_agent_id: str,
    before_table_hash: str,
    after_table_hash: str,
    source_before: str,
    source_after: str,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    if deps.audit_store is None:
        return None
    mandate_seed = (
        f"{organization_id}:{action}:{sender_agent_id}:{recipient_agent_id}:{after_table_hash}"
    )
    mandate_id = f"a2a_trust_{hashlib.sha256(mandate_seed.encode()).hexdigest()[:24]}"
    entry = ComplianceAuditEntry(
        mandate_id=mandate_id,
        subject=f"org:{organization_id}",
        allowed=True,
        reason=f"{action}_applied",
        rule_id=action,
        provider="a2a_trust",
        metadata={
            "event_type": "a2a_trust.relation_change",
            "organization_id": organization_id,
            "actor_organization_id": actor_org_id,
            "sender_agent_id": sender_agent_id,
            "recipient_agent_id": recipient_agent_id,
            "before_table_hash": before_table_hash,
            "after_table_hash": after_table_hash,
            "source_before": source_before,
            "source_after": source_after,
            **(metadata or {}),
        },
    )
    result = deps.audit_store.append(entry)
    if isawaitable(result):
        result = await result
    return str(result or entry.audit_id)


def _normalize_signature_algorithm(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in {"ed25519", "ecdsa-p256", "ecdsa_p256", "p256"}:
        return "ecdsa-p256" if value in {"ecdsa-p256", "ecdsa_p256", "p256"} else "ed25519"
    return ""


def _decode_signature(signature_value: str) -> bytes:
    value = (signature_value or "").strip()
    if not value:
        raise ValueError("missing_signature")

    if value.startswith("0x"):
        value = value[2:]
    if value and all(c in "0123456789abcdefABCDEF" for c in value) and len(value) % 2 == 0:
        try:
            return bytes.fromhex(value)
        except ValueError:
            pass

    padded = value + ("=" * ((4 - len(value) % 4) % 4))
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            return decoder(padded.encode())
        except Exception:  # noqa: BLE001
            continue
    raise ValueError("invalid_signature_encoding")


def _canonical_message_bytes(msg: "A2AMessageRequest") -> bytes:
    payload_json = json.dumps(msg.payload or {}, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
    canonical = "|".join(
        [
            msg.message_id,
            msg.message_type,
            msg.sender_id,
            msg.recipient_id,
            msg.correlation_id or "",
            msg.in_reply_to or "",
            payload_json,
        ]
    )
    return canonical.encode()


async def _verify_a2a_message_signature(
    msg: "A2AMessageRequest",
    deps: "A2ADependencies",
) -> tuple[bool, Optional[str]]:
    signature_present = bool((msg.signature or "").strip())
    if not signature_present:
        if _a2a_signature_required() or not _allow_unsigned_a2a_dev():
            return False, "signature_required"
        return True, None

    if not deps.identity_registry:
        return False, "identity_registry_not_configured"

    identity_record = await deps.identity_registry.get_async(msg.sender_id)
    if not identity_record:
        return False, "sender_identity_not_found"

    expected_domain = os.getenv("SARDIS_A2A_SIGNATURE_DOMAIN", "sardis.sh").strip() or "sardis.sh"
    if not identity_record.is_active(expected_domain):
        return False, "sender_identity_domain_mismatch"

    requested_algorithm = _normalize_signature_algorithm(msg.signature_algorithm)
    if requested_algorithm and requested_algorithm != identity_record.algorithm:
        return False, "signature_algorithm_mismatch"

    try:
        signature_bytes = _decode_signature(msg.signature or "")
    except ValueError as exc:
        return False, str(exc)

    verifier = AgentIdentity(
        agent_id=identity_record.agent_id,
        public_key=identity_record.public_key,
        algorithm=identity_record.algorithm,
        domain=identity_record.domain,
    )
    valid = verifier.verify(
        message=_canonical_message_bytes(msg),
        signature=signature_bytes,
        domain=expected_domain,
        nonce=msg.message_id,
        purpose=f"a2a:{msg.message_type}",
    )
    if not valid:
        return False, "invalid_signature"
    return True, None


# ============================================================================
# Dependencies
# ============================================================================

class A2ADependencies:
    def __init__(
        self,
        wallet_repo: WalletRepository,
        agent_repo: AgentRepository,
        chain_executor: ChainExecutor | None = None,
        wallet_manager: Any | None = None,
        ledger: LedgerStore | None = None,
        compliance: Any | None = None,
        identity_registry: IdentityRegistry | None = None,
        trust_repo: Any | None = None,
        audit_store: Any | None = None,
    ):
        self.wallet_repo = wallet_repo
        self.agent_repo = agent_repo
        self.chain_executor = chain_executor
        self.wallet_manager = wallet_manager
        self.ledger = ledger
        self.compliance = compliance
        self.identity_registry = identity_registry
        self.trust_repo = trust_repo
        self.audit_store = audit_store


def get_deps() -> A2ADependencies:
    raise NotImplementedError("Dependency override required")


# ============================================================================
# Request/Response Models
# ============================================================================

class A2APayRequest(BaseModel):
    """Request for agent-to-agent payment."""
    sender_agent_id: str = Field(..., description="Source agent ID (payer)")
    recipient_agent_id: str = Field(..., description="Destination agent ID (payee)")
    amount: Decimal = Field(..., gt=0, description="Amount in token units (e.g. 10.50)")
    token: str = Field(default="USDC")
    chain: str = Field(default="base_sepolia")
    memo: Optional[str] = Field(default=None, description="Optional memo for audit trail")
    reference: Optional[str] = Field(default=None, description="External reference (order, invoice)")


class A2APayResponse(BaseModel):
    """Response from agent-to-agent payment."""
    success: bool
    tx_hash: str
    status: str
    sender_agent_id: str
    recipient_agent_id: str
    sender_wallet_id: str
    recipient_wallet_id: str
    from_address: str
    to_address: str
    amount: str
    token: str
    chain: str
    memo: Optional[str] = None
    reference: Optional[str] = None
    ledger_tx_id: Optional[str] = None
    audit_anchor: Optional[str] = None


class A2AMessageRequest(BaseModel):
    """Inbound A2A message."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str
    sender_id: str
    recipient_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    signature: Optional[str] = None
    signature_algorithm: str = "Ed25519"


class A2AMessageResponse(BaseModel):
    """Outbound A2A message response."""
    message_id: str
    message_type: str
    sender_id: str
    recipient_id: str
    status: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class A2ATrustCheckRequest(BaseModel):
    sender_agent_id: str
    recipient_agent_id: str


class A2ATrustCheckResponse(BaseModel):
    sender_agent_id: str
    recipient_agent_id: str
    enforced: bool
    allowed: bool
    reason: str
    source: str
    table_hash: str


class A2ATrustTableResponse(BaseModel):
    enforced: bool
    source: str
    table_hash: str
    audit_id: Optional[str] = None
    relations: dict[str, list[str]] = Field(default_factory=dict)


class A2ATrustRelationUpsertRequest(BaseModel):
    sender_agent_id: str
    recipient_agent_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ATrustRelationDeleteRequest(BaseModel):
    sender_agent_id: str
    recipient_agent_id: str


class A2APeerTrustEntry(BaseModel):
    agent_id: str
    owner_id: str
    is_active: bool
    wallet_id: Optional[str] = None
    kya_level: Optional[str] = None
    kya_status: Optional[str] = None
    trusted: bool
    trust_reason: str


class A2ATrustPeersResponse(BaseModel):
    sender_agent_id: str
    enforced: bool
    source: str
    table_hash: str
    total_candidates: int
    trusted_count: int
    peers: list[A2APeerTrustEntry] = Field(default_factory=list)


class A2ATrustAuditEntryResponse(BaseModel):
    audit_id: str
    mandate_id: str
    subject: str
    allowed: bool
    reason: Optional[str] = None
    rule_id: Optional[str] = None
    provider: Optional[str] = None
    evaluated_at: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ATrustAuditListResponse(BaseModel):
    organization_id: str
    count: int
    entries: list[A2ATrustAuditEntryResponse] = Field(default_factory=list)


# ============================================================================
# POST /pay — Agent-to-Agent Direct Payment
# ============================================================================

@router.post("/pay", response_model=A2APayResponse)
async def a2a_pay(
    req: A2APayRequest,
    request: Request,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Execute a direct agent-to-agent payment.

    Transfers tokens from sender agent's wallet to recipient agent's wallet.
    Both agents must exist, have active wallets, and have addresses on the
    specified chain. Policy checks are enforced on the sender's wallet.
    """
    # Idempotency key
    derived = f"a2a:{req.sender_agent_id}:{req.recipient_agent_id}:{req.amount}:{req.token}:{req.chain}:{req.reference or ''}"
    idem_key = get_idempotency_key(request) or derived

    async def _execute() -> tuple[int, object]:
        # Look up sender agent
        sender_agent = await deps.agent_repo.get(req.sender_agent_id)
        if not sender_agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender agent not found")
        if not sender_agent.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender agent is inactive")
        if not principal.is_admin and sender_agent.owner_id != principal.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Look up recipient agent
        recipient_agent = await deps.agent_repo.get(req.recipient_agent_id)
        if not recipient_agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient agent not found")
        if not recipient_agent.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient agent is inactive")
        if (
            not principal.is_admin
            and not _allow_cross_org_a2a()
            and recipient_agent.owner_id != principal.organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cross_org_a2a_disabled",
            )

        trust_ok, trust_reason, _ = await _check_a2a_trust_relation_with_deps(
            deps=deps,
            organization_id=str(principal.organization_id),
            sender_agent_id=req.sender_agent_id,
            recipient_agent_id=req.recipient_agent_id,
        )
        if not trust_ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=trust_reason,
            )

        # Look up sender wallet
        sender_wallet = await deps.wallet_repo.get_by_agent(req.sender_agent_id)
        if not sender_wallet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender agent has no wallet")
        if not sender_wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender wallet is inactive")
        if sender_wallet.is_frozen:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sender wallet is frozen")

        # Look up recipient wallet
        recipient_wallet = await deps.wallet_repo.get_by_agent(req.recipient_agent_id)
        if not recipient_wallet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient agent has no wallet")

        # Get addresses
        sender_address = sender_wallet.get_address(req.chain)
        if not sender_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sender wallet has no address on {req.chain}",
            )

        recipient_address = recipient_wallet.get_address(req.chain)
        if not recipient_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipient wallet has no address on {req.chain}",
            )

        if not deps.chain_executor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chain executor not available",
            )

        # Convert amount to minor units
        try:
            amount_minor = to_raw_token_amount(TokenType(req.token.upper()), req.amount)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported token: {req.token}",
            ) from exc

        # Build payment mandate
        digest = hashlib.sha256(str(idem_key).encode()).hexdigest()
        mandate = PaymentMandate(
            mandate_id=f"a2a_{digest[:16]}",
            mandate_type="payment",
            issuer=f"agent:{req.sender_agent_id}",
            subject=sender_wallet.agent_id,
            expires_at=int(time.time()) + 300,
            nonce=digest,
            proof=VCProof(
                verification_method=f"wallet:{sender_wallet.wallet_id}#key-1",
                created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                proof_value="a2a-transfer",
            ),
            domain="sardis.sh",
            purpose="a2a_transfer",
            chain=req.chain,
            token=req.token,
            amount_minor=amount_minor,
            destination=recipient_address,
            audit_hash=hashlib.sha256(
                f"a2a:{sender_wallet.wallet_id}:{recipient_wallet.wallet_id}:{amount_minor}:{req.memo or ''}".encode()
            ).hexdigest(),
            wallet_id=sender_wallet.wallet_id,
            merchant_domain="sardis.sh",
        )

        # Policy check on sender wallet (MANDATORY - no silent bypass)
        # TODO: Migrate to PaymentOrchestrator gateway
        if not deps.wallet_manager:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="wallet_manager_not_configured",
            )
        policy = await deps.wallet_manager.async_validate_policies(mandate)
        if not getattr(policy, "allowed", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=getattr(policy, "reason", None) or "Policy denied A2A transfer",
            )

        # Compliance (KYC/AML) enforcement
        # TODO: Migrate to PaymentOrchestrator gateway
        if deps.compliance:
            compliance_result = await deps.compliance.preflight(mandate)
            if not compliance_result.allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=compliance_result.reason or "compliance_check_failed",
                )

        # Execute transfer
        try:
            receipt = await deps.chain_executor.dispatch_payment(mandate)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"A2A transfer failed: {e}",
            ) from e

        # Record spend state for policy enforcement
        # TODO: Migrate to PaymentOrchestrator gateway
        if deps.wallet_manager:
            try:
                await deps.wallet_manager.async_record_spend(mandate)
            except Exception as e:
                logger.warning(f"Failed to record spend for A2A pay mandate {mandate.mandate_id}: {e}")

        # Record in ledger
        ledger_tx_id: str | None = None
        if deps.ledger:
            try:
                import inspect
                if hasattr(deps.ledger, "append_async"):
                    maybe_tx = deps.ledger.append_async(payment_mandate=mandate, chain_receipt=receipt)
                else:
                    maybe_tx = deps.ledger.append(payment_mandate=mandate, chain_receipt=receipt)
                tx = await maybe_tx if inspect.isawaitable(maybe_tx) else maybe_tx
                ledger_tx_id = getattr(tx, "tx_id", None)
            except Exception:
                pass

        logger.info(
            f"A2A payment: {req.sender_agent_id} -> {req.recipient_agent_id} | "
            f"{req.amount} {req.token} on {req.chain} | tx={getattr(receipt, 'tx_hash', str(receipt))}"
        )

        return 200, A2APayResponse(
            success=True,
            tx_hash=getattr(receipt, "tx_hash", str(receipt)),
            status="submitted",
            sender_agent_id=req.sender_agent_id,
            recipient_agent_id=req.recipient_agent_id,
            sender_wallet_id=sender_wallet.wallet_id,
            recipient_wallet_id=recipient_wallet.wallet_id,
            from_address=sender_address,
            to_address=recipient_address,
            amount=str(req.amount),
            token=req.token,
            chain=req.chain,
            memo=req.memo,
            reference=req.reference,
            ledger_tx_id=ledger_tx_id,
            audit_anchor=getattr(receipt, "audit_anchor", None),
        )

    return await run_idempotent(
        request=request,
        principal=principal,
        operation="a2a.pay",
        key=str(idem_key),
        payload=req.model_dump(),
        fn=_execute,
    )


# ============================================================================
# POST /messages — Inbound A2A Message Handler
# ============================================================================

@router.post("/messages", response_model=A2AMessageResponse)
async def handle_a2a_message(
    msg: A2AMessageRequest,
    request: Request,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Handle inbound A2A messages (payment requests, credential verifications, etc.).

    Processes structured A2A messages according to the A2A protocol.
    Currently supports: payment_request, credential_request, ack.
    """
    logger.info(f"A2A message received: type={msg.message_type}, from={msg.sender_id}, to={msg.recipient_id}")

    signature_ok, signature_reason = await _verify_a2a_message_signature(msg, deps)
    if not signature_ok:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="error",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=f"A2A signature validation failed: {signature_reason}",
            error_code=signature_reason or "invalid_signature",
        )

    async def _dispatch_message() -> A2AMessageResponse:
        if msg.message_type == "payment_request":
            return await _handle_payment_request(msg, request, deps, principal)
        if msg.message_type == "credential_request":
            return _handle_credential_request(msg)
        if msg.message_type == "ack":
            return A2AMessageResponse(
                message_id=str(uuid.uuid4()),
                message_type="ack",
                sender_id=msg.recipient_id,
                recipient_id=msg.sender_id,
                status="received",
                in_reply_to=msg.message_id,
            )
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="error",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            error=f"Unsupported message type: {msg.message_type}",
            error_code="unsupported_message_type",
        )

    body = await request.body()
    duplicate_response = A2AMessageResponse(
        message_id=msg.message_id,
        message_type="ack",
        sender_id=msg.recipient_id,
        recipient_id=msg.sender_id,
        status="duplicate",
        in_reply_to=msg.message_id,
        correlation_id=msg.correlation_id,
        payload={"deduplicated": True},
    )
    return await run_with_replay_protection(
        request=request,
        provider="a2a",
        event_id=msg.message_id,
        body=body,
        response_on_duplicate=duplicate_response,
        fn=_dispatch_message,
    )


@router.get("/trust/table", response_model=A2ATrustTableResponse)
async def get_a2a_trust_table(
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    table, source = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    if source == "repository_error":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="a2a_trust_repository_unavailable")
    normalized = {sender: sorted(recipients) for sender, recipients in table.items()}
    return A2ATrustTableResponse(
        enforced=_enforce_a2a_trust_table(),
        source=source,
        table_hash=_trust_table_hash(table),
        relations=normalized,
    )


@router.post("/trust/check", response_model=A2ATrustCheckResponse)
async def check_a2a_trust(
    payload: A2ATrustCheckRequest,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        sender_agent = await deps.agent_repo.get(payload.sender_agent_id)
        recipient_agent = await deps.agent_repo.get(payload.recipient_agent_id)
        if (
            sender_agent is None
            or recipient_agent is None
            or sender_agent.owner_id != principal.organization_id
            or recipient_agent.owner_id != principal.organization_id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="access_denied")

    allowed, reason, source = await _check_a2a_trust_relation_with_deps(
        deps=deps,
        organization_id=str(principal.organization_id),
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
    )
    table_hash = _trust_table_hash({})
    if _enforce_a2a_trust_table():
        table, table_source = await _resolve_a2a_trust_table(
            deps=deps,
            organization_id=str(principal.organization_id),
        )
        if table_source != "repository_error":
            table_hash = _trust_table_hash(table)
    return A2ATrustCheckResponse(
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        enforced=_enforce_a2a_trust_table(),
        allowed=allowed,
        reason=reason,
        source=source,
        table_hash=table_hash,
    )


@router.get("/trust/peers", response_model=A2ATrustPeersResponse)
async def list_a2a_trust_peers(
    sender_agent_id: str = Query(..., description="Sender agent to evaluate trust from"),
    include_untrusted: bool = Query(default=False),
    include_inactive: bool = Query(default=False),
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    sender = await deps.agent_repo.get(sender_agent_id)
    if sender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sender_not_found")
    if not principal.is_admin and sender.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="access_denied")

    lister = getattr(deps.agent_repo, "list", None)
    if not callable(lister):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent_repository_list_not_configured")

    org_id = str(sender.owner_id)
    agents = await lister(owner_id=org_id, limit=1000, offset=0)
    if not include_inactive:
        agents = [item for item in agents if bool(getattr(item, "is_active", False))]

    enforced = _enforce_a2a_trust_table()
    if not enforced:
        source = "disabled"
        table: dict[str, set[str]] = {}
    else:
        table, source = await _resolve_a2a_trust_table(deps=deps, organization_id=org_id)
        if source == "repository_error":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="a2a_trust_repository_unavailable")

    rows: list[A2APeerTrustEntry] = []
    trusted_count = 0
    for candidate in agents:
        candidate_id = str(getattr(candidate, "agent_id", ""))
        if not candidate_id or candidate_id == sender_agent_id:
            continue
        if not enforced:
            trusted = True
            reason = "trust_table_not_enforced"
        else:
            trusted, reason = _evaluate_trust_table(
                sender_agent_id=sender_agent_id,
                recipient_agent_id=candidate_id,
                table=table,
            )
        if trusted:
            trusted_count += 1
        if not trusted and not include_untrusted:
            continue
        rows.append(
            A2APeerTrustEntry(
                agent_id=candidate_id,
                owner_id=str(getattr(candidate, "owner_id", "")),
                is_active=bool(getattr(candidate, "is_active", False)),
                wallet_id=getattr(candidate, "wallet_id", None),
                kya_level=getattr(candidate, "kya_level", None),
                kya_status=getattr(candidate, "kya_status", None),
                trusted=trusted,
                trust_reason=reason,
            )
        )

    rows.sort(key=lambda item: (not item.trusted, item.agent_id))
    return A2ATrustPeersResponse(
        sender_agent_id=sender_agent_id,
        enforced=enforced,
        source=source,
        table_hash=_trust_table_hash(table),
        total_candidates=max(len(agents) - 1, 0),
        trusted_count=trusted_count,
        peers=rows,
    )


@router.get("/trust/audit/recent", response_model=A2ATrustAuditListResponse)
async def list_a2a_trust_audit_recent(
    limit: int = Query(default=20, ge=1, le=200),
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    if deps.audit_store is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="audit_store_not_configured")
    getter = getattr(deps.audit_store, "get_recent", None)
    if not callable(getter):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="audit_store_recent_not_supported")
    recent = getter(max(limit * 5, 50))
    if isawaitable(recent):
        recent = await recent
    org_id = str(principal.organization_id)
    out: list[A2ATrustAuditEntryResponse] = []
    for item in recent or []:
        raw = item.to_dict() if hasattr(item, "to_dict") else item
        if not isinstance(raw, dict):
            raw = {
                "audit_id": str(getattr(item, "audit_id", "")),
                "mandate_id": str(getattr(item, "mandate_id", "")),
                "subject": str(getattr(item, "subject", "")),
                "allowed": bool(getattr(item, "allowed", False)),
                "reason": getattr(item, "reason", None),
                "rule_id": getattr(item, "rule_id", None),
                "provider": getattr(item, "provider", None),
                "evaluated_at": str(getattr(item, "evaluated_at", "")),
                "metadata": getattr(item, "metadata", {}) or {},
            }
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        if str(raw.get("provider", "")) != "a2a_trust":
            continue
        if str(metadata.get("organization_id", "")) != org_id:
            continue
        out.append(
            A2ATrustAuditEntryResponse(
                audit_id=str(raw.get("audit_id", "")),
                mandate_id=str(raw.get("mandate_id", "")),
                subject=str(raw.get("subject", "")),
                allowed=bool(raw.get("allowed", False)),
                reason=raw.get("reason"),
                rule_id=raw.get("rule_id"),
                provider=raw.get("provider"),
                evaluated_at=str(raw.get("evaluated_at", "")),
                metadata=metadata,
            )
        )
        if len(out) >= limit:
            break
    return A2ATrustAuditListResponse(
        organization_id=org_id,
        count=len(out),
        entries=out,
    )


@router.post("/trust/relations", response_model=A2ATrustTableResponse)
async def upsert_a2a_trust_relation(
    payload: A2ATrustRelationUpsertRequest,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    repo = getattr(deps, "trust_repo", None)
    upserter = getattr(repo, "upsert_relation", None)
    if not callable(upserter):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="a2a_trust_repository_not_configured")
    table_before, source_before = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    before_hash = _trust_table_hash(table_before)
    await upserter(
        organization_id=str(principal.organization_id),
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        metadata=payload.metadata,
    )
    table, source = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    normalized = {sender: sorted(recipients) for sender, recipients in table.items()}
    after_hash = _trust_table_hash(table)
    audit_id = await _append_a2a_trust_audit_entry(
        deps=deps,
        organization_id=str(principal.organization_id),
        actor_org_id=str(principal.organization_id),
        action="upsert_relation",
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        before_table_hash=before_hash,
        after_table_hash=after_hash,
        source_before=source_before,
        source_after=source,
        metadata={"request_metadata": payload.metadata},
    )
    return A2ATrustTableResponse(
        enforced=_enforce_a2a_trust_table(),
        source=source,
        table_hash=after_hash,
        audit_id=audit_id,
        relations=normalized,
    )


@router.delete("/trust/relations", response_model=A2ATrustTableResponse)
async def delete_a2a_trust_relation(
    payload: A2ATrustRelationDeleteRequest,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    repo = getattr(deps, "trust_repo", None)
    deleter = getattr(repo, "delete_relation", None)
    if not callable(deleter):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="a2a_trust_repository_not_configured")
    table_before, source_before = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    before_hash = _trust_table_hash(table_before)
    deleted = await deleter(
        organization_id=str(principal.organization_id),
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
    )
    table, source = await _resolve_a2a_trust_table(
        deps=deps,
        organization_id=str(principal.organization_id),
    )
    normalized = {sender: sorted(recipients) for sender, recipients in table.items()}
    after_hash = _trust_table_hash(table)
    audit_id = await _append_a2a_trust_audit_entry(
        deps=deps,
        organization_id=str(principal.organization_id),
        actor_org_id=str(principal.organization_id),
        action="delete_relation",
        sender_agent_id=payload.sender_agent_id,
        recipient_agent_id=payload.recipient_agent_id,
        before_table_hash=before_hash,
        after_table_hash=after_hash,
        source_before=source_before,
        source_after=source,
        metadata={"deleted": bool(deleted)},
    )
    return A2ATrustTableResponse(
        enforced=_enforce_a2a_trust_table(),
        source=source,
        table_hash=after_hash,
        audit_id=audit_id,
        relations=normalized,
    )


async def _handle_payment_request(
    msg: A2AMessageRequest,
    request: Request,
    deps: A2ADependencies,
    principal: Principal,
) -> A2AMessageResponse:
    """Handle an inbound A2A payment request."""
    payload = msg.payload
    sender_agent_id = payload.get("sender_agent_id") or msg.sender_id
    recipient_agent_id = payload.get("recipient_agent_id") or msg.recipient_id
    amount_minor = payload.get("amount_minor", 0)
    token = payload.get("token", "USDC")
    chain = payload.get("chain", "base_sepolia")
    destination = payload.get("destination", "")

    if not destination or not amount_minor:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Missing required fields: destination, amount_minor",
            error_code="invalid_request",
        )

    # Validate sender/recipient agents and enforce org boundaries.
    sender_agent = await deps.agent_repo.get(sender_agent_id)
    if not sender_agent:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Sender agent not found",
            error_code="sender_not_found",
        )
    if not sender_agent.is_active:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Sender agent is inactive",
            error_code="sender_inactive",
        )

    recipient_agent = await deps.agent_repo.get(recipient_agent_id)
    if not recipient_agent:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Recipient agent not found",
            error_code="recipient_not_found",
        )
    if not recipient_agent.is_active:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Recipient agent is inactive",
            error_code="recipient_inactive",
        )

    if not principal.is_admin and recipient_agent.owner_id != principal.organization_id:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Access denied",
            error_code="forbidden",
        )
    if (
        not principal.is_admin
        and not _allow_cross_org_a2a()
        and sender_agent.owner_id != principal.organization_id
    ):
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="cross_org_a2a_disabled",
            error_code="forbidden",
        )

    trust_ok, trust_reason, _ = await _check_a2a_trust_relation_with_deps(
        deps=deps,
        organization_id=str(principal.organization_id),
        sender_agent_id=sender_agent_id,
        recipient_agent_id=recipient_agent_id,
    )
    if not trust_ok:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=trust_reason,
            error_code=trust_reason,
        )

    # Look up recipient wallet to execute from
    recipient_wallet = await deps.wallet_repo.get_by_agent(recipient_agent_id)
    if not recipient_wallet:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Recipient agent has no wallet",
            error_code="no_wallet",
        )

    if not deps.chain_executor:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            error="Chain executor not available",
            error_code="service_unavailable",
        )

    # Build mandate
    digest = hashlib.sha256(f"{msg.message_id}:{amount_minor}:{destination}".encode()).hexdigest()
    mandate = PaymentMandate(
        mandate_id=f"a2a_msg_{digest[:16]}",
        mandate_type="payment",
        issuer=f"agent:{sender_agent_id}",
        subject=recipient_wallet.agent_id,
        expires_at=int(time.time()) + 300,
        nonce=digest,
        proof=VCProof(
            verification_method=f"wallet:{recipient_wallet.wallet_id}#key-1",
            created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            proof_value="a2a-message",
        ),
        domain="sardis.sh",
        purpose="a2a_transfer",
        chain=chain,
        token=token,
        amount_minor=amount_minor,
        destination=destination,
        audit_hash=hashlib.sha256(
            f"a2a_msg:{msg.message_id}:{amount_minor}:{destination}".encode()
        ).hexdigest(),
        wallet_id=recipient_wallet.wallet_id,
        merchant_domain="sardis.sh",
    )

    # Policy + Compliance checks for message-based payments (CRITICAL - was previously unprotected)
    # TODO: Migrate to PaymentOrchestrator gateway
    if not deps.wallet_manager:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="wallet_manager_not_configured",
            error_code="configuration_error",
        )
    policy = await deps.wallet_manager.async_validate_policies(mandate)
    if not getattr(policy, "allowed", False):
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=getattr(policy, "reason", None) or "Policy denied payment",
            error_code="policy_denied",
        )

    if not deps.compliance:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="compliance_engine_not_configured",
            error_code="configuration_error",
        )
    try:
        compliance_result = await deps.compliance.preflight(mandate)
        if not compliance_result.allowed:
            return A2AMessageResponse(
                message_id=str(uuid.uuid4()),
                message_type="payment_response",
                sender_id=msg.recipient_id,
                recipient_id=msg.sender_id,
                status="failed",
                in_reply_to=msg.message_id,
                correlation_id=msg.correlation_id,
                error=compliance_result.reason or "compliance_check_failed",
                error_code="compliance_failed",
            )
    except Exception as e:
        logger.error(f"Compliance check failed for A2A message payment: {e}")
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="compliance_service_error",
            error_code="compliance_error",
        )

    try:
        receipt = await deps.chain_executor.dispatch_payment(mandate)
        # Record spend state for policy enforcement
        # TODO: Migrate to PaymentOrchestrator gateway
        if deps.wallet_manager:
            try:
                await deps.wallet_manager.async_record_spend(mandate)
            except Exception:
                logger.warning(f"Failed to record spend for A2A message mandate {mandate.mandate_id}")
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="completed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            payload={
                "success": True,
                "tx_hash": getattr(receipt, "tx_hash", str(receipt)),
                "chain": chain,
                "amount_minor": amount_minor,
                "token": token,
            },
        )
    except Exception as e:
        logger.error(f"A2A payment request failed: {e}")
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=str(e),
            error_code="execution_failed",
        )


def _handle_credential_request(msg: A2AMessageRequest) -> A2AMessageResponse:
    """Handle an inbound credential verification request (stub)."""
    return A2AMessageResponse(
        message_id=str(uuid.uuid4()),
        message_type="credential_response",
        sender_id=msg.recipient_id,
        recipient_id=msg.sender_id,
        status="completed",
        in_reply_to=msg.message_id,
        correlation_id=msg.correlation_id,
        payload={
            "valid": True,
            "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )


# ============================================================================
# GET /agent-card — Sardis Agent Card for A2A Discovery
# ============================================================================

@public_router.get("/agent-card")
async def get_agent_card():
    """
    Return the Sardis agent card for A2A discovery.

    Other agents can use this to discover Sardis capabilities,
    supported tokens/chains, and API endpoints.
    """
    import os

    api_base = os.getenv("SARDIS_API_BASE_URL", "https://sardis-api-staging-ogq6bgc5rq-ue.a.run.app")

    return {
        "agent_id": "sardis-platform",
        "name": "Sardis Payment Agent",
        "version": "2.0.0",
        "description": "Sardis Payment OS - Secure AI payment infrastructure with policy guardrails",
        "operator": {
            "name": "Sardis",
            "url": "https://sardis.sh",
            "contact": "support@sardis.sh",
        },
        "capabilities": [
            "payment.execute",
            "payment.verify",
            "payment.refund",
            "mandate.ingest",
            "mandate.sign",
            "wallet.balance",
            "wallet.hold",
            "checkout.create",
            "checkout.complete",
            "x402.micropay",
        ],
        "payment": {
            "supported_tokens": ["USDC", "USDT", "EURC"],
            "supported_chains": ["base", "polygon", "ethereum", "arbitrum", "optimism"],
            "min_amount_minor": 100,
            "max_amount_minor": 10_000_000,
            "ap2_compliant": True,
            "x402_compliant": True,
            "ucp_compliant": True,
        },
        "endpoints": {
            "api": {
                "url": f"{api_base}/api/v2",
                "protocol": "https",
                "auth_required": True,
                "auth_type": "bearer",
            },
            "a2a": {
                "url": f"{api_base}/api/v2/a2a",
                "protocol": "https",
                "auth_required": True,
                "auth_type": "signature",
            },
            "mcp": "npx @sardis/mcp-server start",
        },
        "a2a_protocol": {
            "version": "1.0",
            "supported_messages": [
                "payment_request",
                "payment_response",
                "credential_request",
                "credential_response",
                "ack",
            ],
            "pay_endpoint": f"{api_base}/api/v2/a2a/pay",
            "messages_endpoint": f"{api_base}/api/v2/a2a/messages",
        },
    }
