"""Agent API endpoints."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sardis_v2_core import Agent, AgentPolicy, AgentRepository, SpendingLimits, WalletRepository
from sardis_v2_core.agent_payment_identity import (
    AgentPaymentIdentity as CanonicalAgentPaymentIdentity,
)
from sardis_v2_core.agent_payment_identity import (
    EvidencePack,
    IdentityAttestation,
    ProvenanceAttestation,
    spend_authority_tier_for_agent,
    trust_tier_from_score,
)

from sardis.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# Request/Response Models
class SpendingLimitsRequest(BaseModel):
    per_transaction: Decimal = Field(default=Decimal("100.00"))
    daily: Decimal = Field(default=Decimal("1000.00"))
    monthly: Decimal = Field(default=Decimal("10000.00"))
    total: Decimal = Field(default=Decimal("100000.00"))


class AgentPolicyRequest(BaseModel):
    allowed_merchants: list[str] | None = None
    blocked_merchants: list[str] = Field(default_factory=list)
    allowed_categories: list[str] | None = None
    blocked_categories: list[str] = Field(default_factory=list)
    require_approval_above: Decimal | None = None
    auto_approve_below: Decimal = Field(default=Decimal("50.00"))


class AgentManifestRequest(BaseModel):
    """KYA Agent Manifest — declares what this agent is authorized to do."""
    capabilities: list[str] = Field(default_factory=list, description="e.g. ['saas_subscription', 'api_credits']")
    max_budget_per_tx: Decimal = Field(default=Decimal("50.00"), description="Max budget per single transaction")
    daily_budget: Decimal = Field(default=Decimal("500.00"), description="Max daily spending budget")
    allowed_domains: list[str] = Field(default_factory=list, description="Merchant domain allowlist")
    blocked_domains: list[str] = Field(default_factory=list, description="Merchant domain blocklist")
    framework: str | None = Field(default=None, description="Agent framework (langchain, crewai, etc.)")
    framework_version: str | None = None


class CreateAgentRequest(BaseModel):
    name: str
    description: str | None = None
    spending_limits: SpendingLimitsRequest | None = None
    policy: AgentPolicyRequest | None = None
    manifest: AgentManifestRequest | None = Field(default=None, description="KYA agent manifest")
    metadata: dict | None = None
    create_wallet: bool = Field(default=True, description="Automatically create a wallet for this agent")
    initial_balance: Decimal = Field(default=Decimal("0.00"))


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    spending_limits: SpendingLimitsRequest | None = None
    policy: AgentPolicyRequest | None = None
    is_active: bool | None = None
    metadata: dict | None = None


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    description: str | None
    owner_id: str
    wallet_id: str | None
    fides_did: str | None = None
    agit_repo_hash: str | None = None
    spending_limits: dict
    policy: dict
    is_active: bool
    kya_level: str
    kya_status: str
    metadata: dict
    created_at: str
    updated_at: str
    last_seen_at: str | None = None
    online_status: str = "unknown"
    session_id: str | None = None
    framework: str | None = None
    sdk_version: str | None = None
    next_steps: list[str] = []

    @classmethod
    def from_agent(cls, agent: Agent, next_steps: list[str] | None = None) -> AgentResponse:
        # Compute online status from last_seen_at (online = seen within last 2 minutes)
        last_seen = getattr(agent, "last_seen_at", None) or agent.metadata.get("last_seen_at")
        online_status = "unknown"
        last_seen_iso = None
        if last_seen is not None:
            if isinstance(last_seen, str):
                try:
                    last_seen = datetime.fromisoformat(last_seen)
                except (ValueError, TypeError):
                    last_seen = None
            if last_seen is not None:
                last_seen_iso = last_seen.isoformat()
                age = datetime.now(UTC) - last_seen
                online_status = "online" if age < timedelta(minutes=2) else "offline"

        return cls(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            owner_id=agent.owner_id,
            wallet_id=agent.wallet_id,
            fides_did=agent.fides_did,
            agit_repo_hash=agent.agit_repo_hash,
            spending_limits=agent.spending_limits.model_dump(),
            policy=agent.policy.model_dump(),
            is_active=agent.is_active,
            kya_level=agent.kya_level,
            kya_status=agent.kya_status,
            metadata=agent.metadata,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
            last_seen_at=last_seen_iso,
            online_status=online_status,
            session_id=getattr(agent, "session_id", None),
            framework=getattr(agent, "framework", None),
            sdk_version=getattr(agent, "sdk_version", None),
            next_steps=next_steps or [],
        )


class CreatePaymentIdentityRequest(BaseModel):
    """One-click payment identity for MCP bootstrap."""

    ttl_seconds: int = Field(default=86400, ge=300, le=604800)
    mode: str = Field(default="live")
    chain: str = Field(default="base_sepolia")
    ensure_wallet: bool = Field(
        default=True,
        description="Create + bind a wallet if the agent does not have one.",
    )


class PaymentIdentityResponse(BaseModel):
    payment_identity_id: str
    agent_id: str
    wallet_id: str
    policy_ref: str
    mode: str
    chain: str
    issued_at: str
    expires_at: str
    mcp_init_snippet: str
    agent_payment_identity: CanonicalAgentPaymentIdentity | None = None
    evidence: EvidencePack | None = None


# Dependency
class AgentDependencies:
    def __init__(self, agent_repo: AgentRepository, wallet_repo: WalletRepository, kya_service=None, wallet_manager=None):
        self.agent_repo = agent_repo
        self.wallet_repo = wallet_repo
        self.kya_service = kya_service
        self.wallet_manager = wallet_manager


def get_deps() -> AgentDependencies:
    raise NotImplementedError("Dependency override required")


def _is_truthy_env(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _kya_auto_registration_enabled() -> bool:
    return _is_truthy_env(os.getenv("SARDIS_KYA_AUTO_REGISTER_ON_AGENT_CREATE", "true"))


def _kya_strict_registration() -> bool:
    explicit = os.getenv("SARDIS_KYA_STRICT_REGISTRATION", "")
    if explicit:
        return _is_truthy_env(explicit)
    return (os.getenv("SARDIS_ENVIRONMENT", "dev") or "dev").strip().lower() in {"prod", "production"}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _identity_secret() -> str:
    secret = os.getenv("SARDIS_SECRET_KEY") or os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "SARDIS_SECRET_KEY or SECRET_KEY environment variable must be set. "
            "Payment identity tokens cannot be signed without a secret."
        )
    return secret


def _sign_identity_payload(payload_b64: str) -> str:
    digest = hmac.new(
        _identity_secret().encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(digest)


def _policy_ref(agent: Agent) -> str:
    policy_payload = json.dumps(
        agent.policy.model_dump(),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(policy_payload.encode("utf-8")).hexdigest()[:16]
    return f"policy_sha256:{digest}"


def _coerce_trust_score(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_fides_did(agent: Agent) -> str | None:
    if agent.fides_did:
        return agent.fides_did
    metadata_value = agent.metadata.get("fides_did")
    if isinstance(metadata_value, str) and metadata_value:
        return metadata_value
    identity_meta = agent.metadata.get("fides_identity")
    if isinstance(identity_meta, dict):
        did_value = identity_meta.get("fides_did")
        if isinstance(did_value, str) and did_value:
            return did_value
    return None


def _build_identity_attestations(agent: Agent, fides_did: str | None) -> list[IdentityAttestation]:
    attestations: list[IdentityAttestation] = []
    if fides_did:
        attestations.append(
            IdentityAttestation(
                kind="fides_did_link",
                reference=fides_did,
                issuer="fides",
                status="active",
            )
        )
    anchor_verification_id = agent.metadata.get("anchor_verification_id")
    if isinstance(anchor_verification_id, str) and anchor_verification_id:
        attestations.append(
            IdentityAttestation(
                kind="anchor_verification",
                reference=anchor_verification_id,
                issuer="sardis",
                status="active",
            )
        )
    code_attestation = agent.metadata.get("code_attestation")
    if isinstance(code_attestation, str) and code_attestation:
        attestations.append(
            IdentityAttestation(
                kind="code_attestation",
                reference=code_attestation,
                issuer="agit",
                status="active",
            )
        )
    return attestations


def _build_provenance(agent: Agent, fides_did: str | None) -> ProvenanceAttestation | None:
    commit_hash = agent.metadata.get("commit_hash")
    code_hash = agent.metadata.get("code_hash")
    repo_hash = agent.agit_repo_hash or agent.metadata.get("agit_repo_hash")
    if not any([repo_hash, commit_hash, code_hash, fides_did]):
        return None
    return ProvenanceAttestation(
        repo_hash=str(repo_hash) if repo_hash else None,
        commit_hash=str(commit_hash) if commit_hash else (str(code_hash) if code_hash else None),
        signer_did=fides_did,
        chain_verified=bool(repo_hash or commit_hash or code_hash),
        source="agit" if repo_hash or commit_hash else "metadata",
    )


def _build_canonical_payment_identity(
    *,
    agent: Agent,
    wallet_id: str | None,
    payment_identity_id: str | None,
    mode: str,
    chain: str,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> CanonicalAgentPaymentIdentity:
    fides_did = _resolve_fides_did(agent)
    trust_metadata = agent.metadata.get("trust")
    trust_score = _coerce_trust_score(agent.metadata.get("trust_score"))
    if trust_score is None and isinstance(trust_metadata, dict):
        trust_score = _coerce_trust_score(trust_metadata.get("score"))
    provenance = _build_provenance(agent, fides_did)
    return CanonicalAgentPaymentIdentity(
        agent_id=agent.agent_id,
        organization_id=agent.owner_id,
        wallet_id=wallet_id,
        payment_identity_id=payment_identity_id,
        did=f"did:sardis:{agent.agent_id}",
        fides_did=fides_did,
        spend_authority_tier=spend_authority_tier_for_agent(
            agent.kya_level,
            has_runtime_provenance=bool(provenance and provenance.commit_hash),
        ),
        kya_level=agent.kya_level,
        kya_status=agent.kya_status,
        policy_ref=_policy_ref(agent),
        mode=mode,
        chain=chain,
        trust_score=trust_score,
        trust_tier=trust_tier_from_score(trust_score),
        identity_attestations=_build_identity_attestations(agent, fides_did),
        provenance=provenance,
        issued_at=issued_at.isoformat() if issued_at else None,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


def _build_evidence_pack(agent: Agent, canonical_identity: CanonicalAgentPaymentIdentity) -> EvidencePack:
    reason_codes = [f"kya:{agent.kya_status}", f"authority:{canonical_identity.spend_authority_tier.value}"]
    if canonical_identity.fides_did:
        reason_codes.append("identity:fides_linked")
    return EvidencePack(
        policy_ref=canonical_identity.policy_ref,
        reason_codes=reason_codes,
        attestation_refs=[att.reference for att in canonical_identity.identity_attestations],
        trust_score=canonical_identity.trust_score,
    )


def _build_payment_identity(
    *,
    principal: Principal,
    agent: Agent,
    wallet_id: str,
    ttl_seconds: int,
    mode: str,
    chain: str,
) -> PaymentIdentityResponse:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(seconds=ttl_seconds)
    payload = {
        "v": 1,
        "org_id": agent.owner_id,
        "agent_id": agent.agent_id,
        "wallet_id": wallet_id,
        "policy_ref": _policy_ref(agent),
        "mode": mode,
        "chain": chain,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = _b64url_encode(payload_json.encode("utf-8"))
    signature_b64 = _sign_identity_payload(payload_b64)
    payment_identity_id = f"spi_{payload_b64}.{signature_b64}"
    canonical_identity = _build_canonical_payment_identity(
        agent=agent,
        wallet_id=wallet_id,
        payment_identity_id=payment_identity_id,
        mode=mode,
        chain=chain,
        issued_at=issued_at,
        expires_at=expires_at,
    )

    return PaymentIdentityResponse(
        payment_identity_id=payment_identity_id,
        agent_id=payload["agent_id"],
        wallet_id=payload["wallet_id"],
        policy_ref=payload["policy_ref"],
        mode=payload["mode"],
        chain=payload["chain"],
        issued_at=issued_at.isoformat(),
        expires_at=expires_at.isoformat(),
        mcp_init_snippet=(
            "npx @sardis/mcp-server init "
            f"--mode {mode} --api-url <API_URL> --api-key <API_KEY> "
            f"--payment-identity {payment_identity_id}"
        ),
        agent_payment_identity=canonical_identity,
        evidence=_build_evidence_pack(agent, canonical_identity),
    )


def _decode_payment_identity(payment_identity_id: str) -> dict:
    if not payment_identity_id.startswith("spi_"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment identity format")
    token = payment_identity_id[4:]
    try:
        payload_b64, signature_b64 = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed payment identity") from exc

    expected = _sign_identity_payload(payload_b64)
    if not hmac.compare_digest(expected, signature_b64):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid payment identity signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment identity payload") from exc

    now_ts = int(datetime.now(UTC).timestamp())
    if int(payload.get("exp", 0)) < now_ts:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Payment identity expired")
    return payload


def _build_mcp_init_snippet(mode: str, payment_identity_id: str) -> str:
    return (
        "npx @sardis/mcp-server init "
        f"--mode {mode} --api-url <API_URL> --api-key <API_KEY> "
        f"--payment-identity {payment_identity_id}"
    )


# Endpoints
@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: CreateAgentRequest,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Create a new AI agent."""
    owner_id = principal.organization_id
    spending_limits = None
    if request.spending_limits:
        spending_limits = SpendingLimits(
            per_transaction=request.spending_limits.per_transaction,
            daily=request.spending_limits.daily,
            monthly=request.spending_limits.monthly,
            total=request.spending_limits.total,
        )

    policy = None
    if request.policy:
        policy = AgentPolicy(
            allowed_merchants=request.policy.allowed_merchants,
            blocked_merchants=request.policy.blocked_merchants,
            allowed_categories=request.policy.allowed_categories,
            blocked_categories=request.policy.blocked_categories,
            require_approval_above=request.policy.require_approval_above,
            auto_approve_below=request.policy.auto_approve_below,
        )

    # Build effective manifest payload for optional KYA auto-registration.
    auto_register_kya = deps.kya_service is not None and _kya_auto_registration_enabled()
    manifest_payload = {
        "capabilities": request.manifest.capabilities if request.manifest else [],
        "max_budget_per_tx": str(
            request.manifest.max_budget_per_tx
            if request.manifest
            else (spending_limits.per_transaction if spending_limits else Decimal("100.00"))
        ),
        "daily_budget": str(
            request.manifest.daily_budget
            if request.manifest
            else (spending_limits.daily if spending_limits else Decimal("1000.00"))
        ),
        "allowed_domains": request.manifest.allowed_domains if request.manifest else [],
        "blocked_domains": request.manifest.blocked_domains if request.manifest else [],
        "framework": request.manifest.framework if request.manifest else None,
        "framework_version": request.manifest.framework_version if request.manifest else None,
    }

    # Persist manifest metadata when user supplied one, or when auto-registration is enabled.
    agent_metadata = dict(request.metadata or {})
    if request.manifest or auto_register_kya:
        agent_metadata["manifest"] = manifest_payload

    kya_level = "basic" if auto_register_kya else ("basic" if request.manifest else "none")
    kya_status = "active" if auto_register_kya else ("active" if request.manifest else "pending")

    agent = await deps.agent_repo.create(
        name=request.name,
        owner_id=owner_id,
        description=request.description,
        spending_limits=spending_limits,
        policy=policy,
        metadata=agent_metadata,
        kya_level=kya_level,
        kya_status=kya_status,
    )

    if auto_register_kya:
        strict_kya_registration = _kya_strict_registration()
        try:
            from sardis_compliance.kya import AgentManifest

            kya_result = await deps.kya_service.register_agent(
                AgentManifest(
                    agent_id=agent.agent_id,
                    owner_id=owner_id,
                    capabilities=manifest_payload["capabilities"],
                    max_budget_per_tx=Decimal(manifest_payload["max_budget_per_tx"]),
                    daily_budget=Decimal(manifest_payload["daily_budget"]),
                    allowed_domains=manifest_payload["allowed_domains"],
                    blocked_domains=manifest_payload["blocked_domains"],
                    framework=manifest_payload["framework"],
                    framework_version=manifest_payload["framework_version"],
                    description=request.description,
                    metadata=agent_metadata,
                )
            )
            updated_agent = await deps.agent_repo.update(
                agent_id=agent.agent_id,
                kya_level=kya_result.level.value,
                kya_status=kya_result.status.value,
            )
            if updated_agent is not None:
                agent = updated_agent
        except Exception as exc:
            logger.error("KYA auto-registration failed for agent %s: %s", agent.agent_id, exc)
            if strict_kya_registration:
                await deps.agent_repo.delete(agent.agent_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="kya_registration_failed",
                ) from exc
            downgraded = await deps.agent_repo.update(
                agent_id=agent.agent_id,
                kya_level="none",
                kya_status="pending",
            )
            if downgraded is not None:
                agent = downgraded

    # Optionally create a wallet for the agent
    if request.create_wallet:
        addresses: dict[str, str] | None = None
        wallet_id_override: str | None = None

        # Call Turnkey to create a real MPC wallet with an on-chain address
        if deps.wallet_manager:
            try:
                provider_result = await deps.wallet_manager.create_turnkey_wallet(
                    wallet_name=f"agent_{agent.agent_id}",
                    agent_id=agent.agent_id,
                )
                wallet_id_override = provider_result.get("wallet_id")
                addrs = provider_result.get("addresses") or []
                first_addr = None
                if addrs:
                    first_addr = addrs[0].get("address") if isinstance(addrs[0], dict) else addrs[0]
                if isinstance(first_addr, str) and first_addr:
                    addresses = {
                        "base_sepolia": first_addr, "base": first_addr,
                        "ethereum": first_addr, "polygon": first_addr,
                        "arbitrum": first_addr, "optimism": first_addr,
                        "tempo": first_addr,
                    }
            except Exception as e:
                logger.warning("Turnkey wallet creation failed for agent %s: %s", agent.agent_id, e)
                # Fall through — wallet will be created without addresses (can be fixed later)

        wallet = await deps.wallet_repo.create(
            agent_id=agent.agent_id,
            wallet_id=wallet_id_override,
            mpc_provider="turnkey",
            currency="USDC",
            limit_per_tx=spending_limits.per_transaction if spending_limits else Decimal("100.00"),
            limit_total=spending_limits.total if spending_limits else Decimal("1000.00"),
            addresses=addresses,
        )
        await deps.agent_repo.bind_wallet(agent.agent_id, wallet.wallet_id)
        agent.wallet_id = wallet.wallet_id

    # Analytics: track agent creation (fire-and-forget, never blocks the request)
    from sardis.analytics.posthog_tracker import FIRST_AGENT_CREATED, track_event
    track_event(principal.user_id, FIRST_AGENT_CREATED, {"agent_name": agent.name})

    return AgentResponse.from_agent(agent, next_steps=[
        "POST /api/v2/mpp/sessions — Start MPP payment session",
        "POST /api/v2/spending-mandates — Set spending policy",
    ])


@router.get("")
async def list_agents(
    owner_id: str | None = Query(None),
    is_active: bool | None = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """List all agents."""
    effective_owner = owner_id if (principal.is_admin and owner_id) else principal.organization_id
    agents = await deps.agent_repo.list(
        owner_id=effective_owner,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    items = [AgentResponse.from_agent(a) for a in agents]
    return {"items": items, "total": len(items), "limit": limit, "offset": offset}


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get agent details."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return AgentResponse.from_agent(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Update agent settings."""
    existing = await deps.agent_repo.get(agent_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and existing.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    spending_limits = None
    if request.spending_limits:
        spending_limits = SpendingLimits(
            per_transaction=request.spending_limits.per_transaction,
            daily=request.spending_limits.daily,
            monthly=request.spending_limits.monthly,
            total=request.spending_limits.total,
        )

    policy = None
    if request.policy:
        policy = AgentPolicy(
            allowed_merchants=request.policy.allowed_merchants,
            blocked_merchants=request.policy.blocked_merchants,
            allowed_categories=request.policy.allowed_categories,
            blocked_categories=request.policy.blocked_categories,
            require_approval_above=request.policy.require_approval_above,
            auto_approve_below=request.policy.auto_approve_below,
        )

    agent = await deps.agent_repo.update(
        agent_id,
        name=request.name,
        description=request.description,
        spending_limits=spending_limits,
        policy=policy,
        is_active=request.is_active,
        metadata=request.metadata,
    )
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse.from_agent(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Delete an agent."""
    existing = await deps.agent_repo.get(agent_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and existing.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    deleted = await deps.agent_repo.delete(agent_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")


@router.post("/{agent_id}/payment-identity", response_model=PaymentIdentityResponse)
async def create_payment_identity(
    agent_id: str,
    request: CreatePaymentIdentityRequest,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Create a signed payment identity used by MCP bootstrap.

    This endpoint provides the "one-click" artifact a developer can pass to:
      npx @sardis/mcp-server init --payment-identity <id>
    """
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    wallet_id = agent.wallet_id
    if not wallet_id and request.ensure_wallet:
        pi_addresses: dict[str, str] | None = None
        pi_wallet_id_override: str | None = None

        # Call Turnkey to create a real MPC wallet with an on-chain address
        if deps.wallet_manager:
            try:
                pi_result = await deps.wallet_manager.create_turnkey_wallet(
                    wallet_name=f"agent_{agent.agent_id}",
                    agent_id=agent.agent_id,
                )
                pi_wallet_id_override = pi_result.get("wallet_id")
                pi_addrs = pi_result.get("addresses") or []
                pi_first = None
                if pi_addrs:
                    pi_first = pi_addrs[0].get("address") if isinstance(pi_addrs[0], dict) else pi_addrs[0]
                if isinstance(pi_first, str) and pi_first:
                    pi_addresses = {
                        "base_sepolia": pi_first, "base": pi_first,
                        "ethereum": pi_first, "polygon": pi_first,
                        "arbitrum": pi_first, "optimism": pi_first,
                        "tempo": pi_first,
                    }
            except Exception as e:
                logger.warning("Turnkey wallet creation failed for payment identity %s: %s", agent.agent_id, e)

        wallet = await deps.wallet_repo.create(
            agent_id=agent.agent_id,
            wallet_id=pi_wallet_id_override,
            mpc_provider="turnkey",
            currency="USDC",
            limit_per_tx=agent.spending_limits.per_transaction,
            limit_total=agent.spending_limits.total,
            addresses=pi_addresses,
        )
        wallet_id = wallet.wallet_id
        await deps.agent_repo.bind_wallet(agent.agent_id, wallet_id)
        agent.wallet_id = wallet_id

    if not wallet_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent has no wallet. Bind or create a wallet before creating payment identity.",
        )

    return _build_payment_identity(
        principal=principal,
        agent=agent,
        wallet_id=wallet_id,
        ttl_seconds=request.ttl_seconds,
        mode=request.mode,
        chain=request.chain,
    )


@router.get("/payment-identities/{payment_identity_id}", response_model=PaymentIdentityResponse)
async def resolve_payment_identity(
    payment_identity_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Resolve a signed payment identity for MCP initialization."""
    payload = _decode_payment_identity(payment_identity_id)

    payload_org = str(payload.get("org_id", ""))
    if not principal.is_admin and payload_org != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    agent_id = str(payload.get("agent_id", ""))
    wallet_id = str(payload.get("wallet_id", ""))
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    issued_at = datetime.fromtimestamp(int(payload.get("iat", 0)), tz=UTC)
    expires_at = datetime.fromtimestamp(int(payload.get("exp", 0)), tz=UTC)

    mode = str(payload.get("mode") or "live")
    chain = str(payload.get("chain") or "base_sepolia")
    policy_ref = str(payload.get("policy_ref") or _policy_ref(agent))
    canonical_identity = _build_canonical_payment_identity(
        agent=agent,
        wallet_id=wallet_id,
        payment_identity_id=payment_identity_id,
        mode=mode,
        chain=chain,
        issued_at=issued_at,
        expires_at=expires_at,
    )

    return PaymentIdentityResponse(
        payment_identity_id=payment_identity_id,
        agent_id=agent_id,
        wallet_id=wallet_id,
        policy_ref=policy_ref,
        mode=mode,
        chain=chain,
        issued_at=issued_at.isoformat(),
        expires_at=expires_at.isoformat(),
        mcp_init_snippet=_build_mcp_init_snippet(mode, payment_identity_id),
        agent_payment_identity=canonical_identity,
        evidence=_build_evidence_pack(agent, canonical_identity),
    )


@router.get("/{agent_id}/agent-payment-identity", response_model=CanonicalAgentPaymentIdentity)
async def get_agent_payment_identity(
    agent_id: str,
    mode: str = Query(default="live"),
    chain: str = Query(default="base_sepolia"),
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Return the canonical agent payment identity profile used across rails."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _build_canonical_payment_identity(
        agent=agent,
        wallet_id=agent.wallet_id,
        payment_identity_id=None,
        mode=mode,
        chain=chain,
    )


@router.post("/{agent_id}/wallet", response_model=AgentResponse)
async def bind_wallet_to_agent(
    agent_id: str,
    wallet_id: str = Query(...),
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Bind an existing wallet to an agent."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Verify wallet exists
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    agent = await deps.agent_repo.bind_wallet(agent_id, wallet_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse.from_agent(agent)


class InstructAgentRequest(BaseModel):
    instruction: str = Field(description="Natural language instruction for the agent")


class InstructAgentResponse(BaseModel):
    agent_id: str
    instruction: str
    response: str
    tool_call: dict | None = None
    tx_id: str | None = None
    error: str | None = None


@router.post("/{agent_id}/instruct", response_model=InstructAgentResponse)
async def instruct_agent(
    agent_id: str,
    request: InstructAgentRequest,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Send a natural language instruction to an agent for policy-checked execution."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    instruction = request.instruction.lower().strip()

    # Simple instruction parsing for demo
    if any(kw in instruction for kw in ["balance", "how much", "funds", "wallet"]):
        wallet = None
        if agent.wallet_id:
            wallet = await deps.wallet_repo.get(agent.wallet_id)
        if wallet:
            return InstructAgentResponse(
                agent_id=agent_id,
                instruction=request.instruction,
                response=f"Your wallet ({wallet.wallet_id}) has spending limits of ${float(wallet.limit_per_tx):.2f} per transaction and ${float(wallet.limit_total):.2f} total. Currency: {wallet.currency}.",
                tool_call={"name": "get_wallet_balance", "arguments": {"wallet_id": wallet.wallet_id}},
            )
        return InstructAgentResponse(
            agent_id=agent_id,
            instruction=request.instruction,
            response="No wallet is currently bound to this agent. Create one via the Dashboard or API.",
        )

    if any(kw in instruction for kw in ["policy", "limit", "rules", "spending"]):
        sl = agent.spending_limits
        return InstructAgentResponse(
            agent_id=agent_id,
            instruction=request.instruction,
            response=f"Current spending policy: ${float(sl.per_transaction):.2f}/tx, ${float(sl.daily):.2f}/day, ${float(sl.monthly):.2f}/month, ${float(sl.total):.2f} total limit.",
            tool_call={"name": "get_spending_policy", "arguments": {"agent_id": agent_id}},
        )

    if any(kw in instruction for kw in ["buy", "purchase", "pay", "send", "transfer"]):
        sl = agent.spending_limits
        return InstructAgentResponse(
            agent_id=agent_id,
            instruction=request.instruction,
            response=f"I can process payments within my spending policy (${float(sl.per_transaction):.2f}/tx limit). To execute a payment, use the simulate-purchase endpoint or provide a specific amount and merchant.",
            tool_call={"name": "evaluate_payment_intent", "arguments": {"instruction": request.instruction}},
        )

    # Default response
    return InstructAgentResponse(
        agent_id=agent_id,
        instruction=request.instruction,
        response=f"I'm {agent.name}, a Sardis-managed AI agent. I can help with: checking balances, reviewing spending policies, and processing payments within my authorized limits. What would you like to do?",
    )


@router.get("/{agent_id}/limits", response_model=dict)
async def get_agent_limits(
    agent_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get current spending limits and usage for an agent."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    wallet = None
    if agent.wallet_id:
        wallet = await deps.wallet_repo.get(agent.wallet_id)

    return {
        "agent_id": agent.agent_id,
        "spending_limits": agent.spending_limits.model_dump(),
        "wallet": {
            "wallet_id": wallet.wallet_id if wallet else None,
            "addresses": wallet.addresses if wallet else {},
            "mpc_provider": wallet.mpc_provider if wallet else None,
        } if wallet else None,
    }


# ============ KYA (Know Your Agent) Endpoints ============


class KYAStatusResponse(BaseModel):
    agent_id: str
    kya_level: str
    kya_status: str
    manifest: dict | None = None
    trust_score: float | None = None


class KYAUpgradeRequest(BaseModel):
    target_level: str = Field(description="Target KYA level: basic, verified, or attested")
    anchor_verification_id: str | None = Field(default=None, description="Owner KYC verification ID (required for verified)")
    code_hash: str | None = Field(default=None, description="SHA-256 hash of agent code (required for attested)")
    framework: str | None = Field(default=None, description="Agent framework name")


class KYAUpgradeResponse(BaseModel):
    agent_id: str
    previous_level: str
    new_level: str
    status: str
    reason: str | None = None


@router.get("/{agent_id}/kya", response_model=KYAStatusResponse)
async def get_agent_kya(
    agent_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get KYA (Know Your Agent) status for an agent."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return KYAStatusResponse(
        agent_id=agent.agent_id,
        kya_level=agent.kya_level,
        kya_status=agent.kya_status,
        manifest=agent.metadata.get("manifest"),
        trust_score=agent.metadata.get("trust_score"),
    )


@router.post("/{agent_id}/kya/upgrade", response_model=KYAUpgradeResponse)
async def upgrade_agent_kya(
    agent_id: str,
    request: KYAUpgradeRequest,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Request a KYA level upgrade for an agent."""
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    target = request.target_level.lower()
    valid_levels = {"basic", "verified", "attested"}
    if target not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target level. Must be one of: {', '.join(valid_levels)}",
        )

    previous_level = agent.kya_level

    # Validate upgrade requirements
    if target == "verified" and not request.anchor_verification_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="anchor_verification_id is required for VERIFIED level (owner KYC)",
        )

    if target == "attested" and not request.code_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="code_hash is required for ATTESTED level",
        )

    # Store attestation data in metadata
    meta = agent.metadata or {}
    if request.anchor_verification_id:
        meta["anchor_verification_id"] = request.anchor_verification_id
    if request.code_hash:
        meta["code_attestation"] = {
            "code_hash": request.code_hash,
            "framework": request.framework,
        }

    # Perform upgrade
    await deps.agent_repo.update(
        agent_id,
        kya_level=target,
        kya_status="active",
        metadata=meta,
    )

    return KYAUpgradeResponse(
        agent_id=agent_id,
        previous_level=previous_level,
        new_level=target,
        status="active",
        reason=f"upgraded_to_{target}",
    )


@router.post("/{agent_id}/kya/suspend", response_model=KYAStatusResponse)
async def suspend_agent_kya(
    agent_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Suspend an agent's KYA status (admin only)."""
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    await deps.agent_repo.update(agent_id, kya_status="suspended")

    return KYAStatusResponse(
        agent_id=agent.agent_id,
        kya_level=agent.kya_level,
        kya_status="suspended",
        manifest=agent.metadata.get("manifest"),
    )


@router.post("/{agent_id}/kya/reactivate", response_model=KYAStatusResponse)
async def reactivate_agent_kya(
    agent_id: str,
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Reactivate a suspended agent's KYA status (admin only)."""
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.kya_status != "suspended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent is not suspended (current status: {agent.kya_status})",
        )

    await deps.agent_repo.update(agent_id, kya_status="active")

    return KYAStatusResponse(
        agent_id=agent.agent_id,
        kya_level=agent.kya_level,
        kya_status="active",
        manifest=agent.metadata.get("manifest"),
    )


# ── Spend Widget Endpoint ──────────────────────────────────────────────

class SpendingBudgetResponse(BaseModel):
    used: Decimal
    total: Decimal
    period: str


class SpendingChartPoint(BaseModel):
    date: str
    amount: Decimal


class SpendingTransactionExplanation(BaseModel):
    checks_failed: list[str]
    suggested_action: str


class SpendingTransaction(BaseModel):
    id: str
    date: str
    recipient: str
    amount: Decimal
    status: str
    explanation: SpendingTransactionExplanation | None = None


class AgentSpendingResponse(BaseModel):
    budget: SpendingBudgetResponse
    chart: list[SpendingChartPoint]
    transactions: list[SpendingTransaction]


_spending_cache: dict[str, tuple[float, AgentSpendingResponse]] = {}
_SPENDING_CACHE_TTL = 30  # seconds


@router.get("/{agent_id}/spending", response_model=AgentSpendingResponse)
async def get_agent_spending(
    agent_id: str,
    period: str = Query(default="7d", pattern="^(7d|30d)$"),
    deps: AgentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Return spending summary for the spend widget: budget, chart, transactions."""
    import time

    cache_key = f"{agent_id}:{period}"
    now = time.time()
    if cache_key in _spending_cache:
        ts, cached = _spending_cache[cache_key]
        if now - ts < _SPENDING_CACHE_TTL:
            return cached

    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.owner_id != principal.user_id and not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    days = 7 if period == "7d" else 30
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Query execution receipts for this agent
    budget_total = Decimal(str(agent.spending_limits.daily)) * days
    budget_used = Decimal("0")
    chart_data: dict[str, Decimal] = {}
    txns: list[SpendingTransaction] = []

    try:
        from sardis_v2_core import get_db_pool

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, created_at, recipient, amount, status, metadata
                FROM execution_receipts
                WHERE agent_id = $1 AND created_at >= $2
                ORDER BY created_at DESC
                LIMIT 200
                """,
                agent_id,
                cutoff,
            )

            for row in rows:
                amt = Decimal(str(row["amount"]))
                if row["status"] == "completed":
                    budget_used += amt
                day_key = row["created_at"].strftime("%b %d")
                chart_data[day_key] = chart_data.get(day_key, Decimal("0")) + amt

                explanation = None
                if row["status"] == "blocked" and row.get("metadata"):
                    meta = row["metadata"] if isinstance(row["metadata"], dict) else {}
                    if "checks_failed" in meta:
                        explanation = SpendingTransactionExplanation(
                            checks_failed=meta["checks_failed"],
                            suggested_action=meta.get("suggested_action", "Contact admin"),
                        )

                txns.append(
                    SpendingTransaction(
                        id=row["id"],
                        date=row["created_at"].strftime("%Y-%m-%d"),
                        recipient=row.get("recipient", "Unknown"),
                        amount=amt,
                        status=row["status"],
                        explanation=explanation,
                    )
                )
    except Exception:
        logger.warning("Failed to query execution_receipts for spending widget, returning empty data")

    # Build chart points for each day in range
    chart: list[SpendingChartPoint] = []
    for i in range(days):
        day = datetime.now(UTC) - timedelta(days=days - 1 - i)
        key = day.strftime("%b %d")
        chart.append(SpendingChartPoint(date=key, amount=chart_data.get(key, Decimal("0"))))

    result = AgentSpendingResponse(
        budget=SpendingBudgetResponse(used=budget_used, total=budget_total, period=period),
        chart=chart,
        transactions=txns[:50],
    )

    _spending_cache[cache_key] = (now, result)
    return result
