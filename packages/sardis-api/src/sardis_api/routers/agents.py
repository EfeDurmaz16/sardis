"""Agent API endpoints."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from sardis_v2_core import Agent, AgentPolicy, SpendingLimits, AgentRepository, WalletRepository
from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])


# Request/Response Models
class SpendingLimitsRequest(BaseModel):
    per_transaction: Decimal = Field(default=Decimal("100.00"))
    daily: Decimal = Field(default=Decimal("1000.00"))
    monthly: Decimal = Field(default=Decimal("10000.00"))
    total: Decimal = Field(default=Decimal("100000.00"))


class AgentPolicyRequest(BaseModel):
    allowed_merchants: Optional[List[str]] = None
    blocked_merchants: List[str] = Field(default_factory=list)
    allowed_categories: Optional[List[str]] = None
    blocked_categories: List[str] = Field(default_factory=list)
    require_approval_above: Optional[Decimal] = None
    auto_approve_below: Decimal = Field(default=Decimal("50.00"))


class AgentManifestRequest(BaseModel):
    """KYA Agent Manifest — declares what this agent is authorized to do."""
    capabilities: List[str] = Field(default_factory=list, description="e.g. ['saas_subscription', 'api_credits']")
    max_budget_per_tx: Decimal = Field(default=Decimal("50.00"), description="Max budget per single transaction")
    daily_budget: Decimal = Field(default=Decimal("500.00"), description="Max daily spending budget")
    allowed_domains: List[str] = Field(default_factory=list, description="Merchant domain allowlist")
    blocked_domains: List[str] = Field(default_factory=list, description="Merchant domain blocklist")
    framework: Optional[str] = Field(default=None, description="Agent framework (langchain, crewai, etc.)")
    framework_version: Optional[str] = None


class CreateAgentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    spending_limits: Optional[SpendingLimitsRequest] = None
    policy: Optional[AgentPolicyRequest] = None
    manifest: Optional[AgentManifestRequest] = Field(default=None, description="KYA agent manifest")
    metadata: Optional[dict] = None
    create_wallet: bool = Field(default=True, description="Automatically create a wallet for this agent")
    initial_balance: Decimal = Field(default=Decimal("0.00"))


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    spending_limits: Optional[SpendingLimitsRequest] = None
    policy: Optional[AgentPolicyRequest] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    description: Optional[str]
    owner_id: str
    wallet_id: Optional[str]
    spending_limits: dict
    policy: dict
    is_active: bool
    kya_level: str
    kya_status: str
    metadata: dict
    created_at: str
    updated_at: str

    @classmethod
    def from_agent(cls, agent: Agent) -> "AgentResponse":
        return cls(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            owner_id=agent.owner_id,
            wallet_id=agent.wallet_id,
            spending_limits=agent.spending_limits.model_dump(),
            policy=agent.policy.model_dump(),
            is_active=agent.is_active,
            kya_level=agent.kya_level,
            kya_status=agent.kya_status,
            metadata=agent.metadata,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
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


# Dependency
class AgentDependencies:
    def __init__(self, agent_repo: AgentRepository, wallet_repo: WalletRepository):
        self.agent_repo = agent_repo
        self.wallet_repo = wallet_repo


def get_deps() -> AgentDependencies:
    raise NotImplementedError("Dependency override required")


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


def _build_payment_identity(
    *,
    principal: Principal,
    agent: Agent,
    wallet_id: str,
    ttl_seconds: int,
    mode: str,
    chain: str,
) -> PaymentIdentityResponse:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(seconds=ttl_seconds)
    payload = {
        "v": 1,
        "org_id": principal.organization_id,
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

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if int(payload.get("exp", 0)) < now_ts:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Payment identity expired")
    return payload


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

    # Merge manifest into metadata if provided
    agent_metadata = request.metadata or {}
    kya_level = "none"
    kya_status = "pending"
    if request.manifest:
        agent_metadata["manifest"] = {
            "capabilities": request.manifest.capabilities,
            "max_budget_per_tx": str(request.manifest.max_budget_per_tx),
            "daily_budget": str(request.manifest.daily_budget),
            "allowed_domains": request.manifest.allowed_domains,
            "blocked_domains": request.manifest.blocked_domains,
            "framework": request.manifest.framework,
            "framework_version": request.manifest.framework_version,
        }
        # Agents registered with a manifest start at BASIC level
        kya_level = "basic"
        kya_status = "active"

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

    # Optionally create a wallet for the agent
    if request.create_wallet:
        wallet = await deps.wallet_repo.create(
            agent_id=agent.agent_id,
            mpc_provider="turnkey",
            currency="USDC",
            limit_per_tx=spending_limits.per_transaction if spending_limits else Decimal("100.00"),
            limit_total=spending_limits.total if spending_limits else Decimal("1000.00"),
        )
        await deps.agent_repo.bind_wallet(agent.agent_id, wallet.wallet_id)
        agent.wallet_id = wallet.wallet_id

    return AgentResponse.from_agent(agent)


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    owner_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
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
    return [AgentResponse.from_agent(a) for a in agents]


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
        wallet = await deps.wallet_repo.create(
            agent_id=agent.agent_id,
            mpc_provider="turnkey",
            currency="USDC",
            limit_per_tx=agent.spending_limits.per_transaction,
            limit_total=agent.spending_limits.total,
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

    issued_at = datetime.fromtimestamp(int(payload.get("iat", 0)), tz=timezone.utc)
    expires_at = datetime.fromtimestamp(int(payload.get("exp", 0)), tz=timezone.utc)

    mode = str(payload.get("mode") or "live")
    chain = str(payload.get("chain") or "base_sepolia")
    policy_ref = str(payload.get("policy_ref") or _policy_ref(agent))

    return PaymentIdentityResponse(
        payment_identity_id=payment_identity_id,
        agent_id=agent_id,
        wallet_id=wallet_id,
        policy_ref=policy_ref,
        mode=mode,
        chain=chain,
        issued_at=issued_at.isoformat(),
        expires_at=expires_at.isoformat(),
        mcp_init_snippet=(
            "npx @sardis/mcp-server init "
            f"--mode {mode} --api-url <API_URL> --api-key <API_KEY> "
            f"--payment-identity {payment_identity_id}"
        ),
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
    tool_call: Optional[dict] = None
    tx_id: Optional[str] = None
    error: Optional[str] = None


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
