"""Environment templates for sandbox, test, and controlled live lanes.

Pre-built configurations that reduce setup time for design partner pilots.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class ProviderConfig(BaseModel):
    name: str
    required: bool
    env_var: str
    status: str = "not_configured"  # configured, not_configured, optional
    docs_url: str = ""


class EnvironmentTemplate(BaseModel):
    id: str
    name: str
    description: str
    lane: str  # "sandbox", "test", "live"
    providers: list[ProviderConfig]
    env_vars: dict[str, str]  # Default env var values
    policy_defaults: str  # NL policy text
    safety_defaults: dict  # Kill switch, freeze settings
    recommended_for: list[str]  # e.g., ["api-procurement", "browser-use"]


TEMPLATES: list[EnvironmentTemplate] = [
    EnvironmentTemplate(
        id="sandbox-default",
        name="Sandbox Starter",
        description="Zero-config sandbox for exploring Sardis. No real payments, no external providers needed.",
        lane="sandbox",
        providers=[
            ProviderConfig(
                name="Database",
                required=False,
                env_var="DATABASE_URL",
                status="optional",
                docs_url="https://sardis.sh/docs/setup#database",
            ),
        ],
        env_vars={"SARDIS_ENV": "sandbox", "SARDIS_CHAIN": "base_sepolia"},
        policy_defaults="Max $100 per transaction. Daily limit $500. All merchants allowed.",
        safety_defaults={"kill_switch": "off", "auto_freeze": False},
        recommended_for=["first-time-setup", "demo", "evaluation"],
    ),
    EnvironmentTemplate(
        id="test-integration",
        name="Test Integration",
        description="Testnet integration with real API calls but no real money. Connects to external providers in test mode.",
        lane="test",
        providers=[
            ProviderConfig(
                name="Database",
                required=True,
                env_var="DATABASE_URL",
                status="not_configured",
                docs_url="https://sardis.sh/docs/setup#database",
            ),
            ProviderConfig(
                name="Turnkey (MPC)",
                required=True,
                env_var="TURNKEY_API_KEY",
                status="not_configured",
                docs_url="https://sardis.sh/docs/setup#turnkey",
            ),
            ProviderConfig(
                name="Alchemy (RPC)",
                required=True,
                env_var="SARDIS_BASE_RPC_URL",
                status="not_configured",
                docs_url="https://sardis.sh/docs/setup#rpc",
            ),
            ProviderConfig(
                name="Stripe (Cards)",
                required=False,
                env_var="STRIPE_SECRET_KEY",
                status="optional",
                docs_url="https://sardis.sh/docs/setup#stripe",
            ),
            ProviderConfig(
                name="Redis (Cache)",
                required=False,
                env_var="SARDIS_REDIS_URL",
                status="optional",
                docs_url="https://sardis.sh/docs/setup#redis",
            ),
        ],
        env_vars={
            "SARDIS_ENV": "test",
            "SARDIS_CHAIN": "base_sepolia",
            "SARDIS_AGIT_FAIL_OPEN": "false",
        },
        policy_defaults="Max $500 per transaction. Daily limit $2,000. Require approval above $200. Block gambling MCCs.",
        safety_defaults={
            "kill_switch": "off",
            "auto_freeze": True,
            "webhook_signatures": True,
        },
        recommended_for=["api-procurement", "browser-use", "crewai"],
    ),
    EnvironmentTemplate(
        id="live-controlled",
        name="Controlled Live",
        description="Production environment with real payments, full compliance, and operator controls. Requires KYC and billing.",
        lane="live",
        providers=[
            ProviderConfig(
                name="Database",
                required=True,
                env_var="DATABASE_URL",
                status="not_configured",
                docs_url="https://sardis.sh/docs/setup#database",
            ),
            ProviderConfig(
                name="Turnkey (MPC)",
                required=True,
                env_var="TURNKEY_API_KEY",
                status="not_configured",
                docs_url="https://sardis.sh/docs/setup#turnkey",
            ),
            ProviderConfig(
                name="Alchemy (RPC)",
                required=True,
                env_var="SARDIS_BASE_RPC_URL",
                status="not_configured",
                docs_url="https://sardis.sh/docs/setup#rpc",
            ),
            ProviderConfig(
                name="Stripe (Cards)",
                required=True,
                env_var="STRIPE_SECRET_KEY",
                status="not_configured",
                docs_url="https://sardis.sh/docs/setup#stripe",
            ),
            ProviderConfig(
                name="Redis (Cache)",
                required=True,
                env_var="SARDIS_REDIS_URL",
                status="not_configured",
                docs_url="https://sardis.sh/docs/setup#redis",
            ),
            ProviderConfig(
                name="iDenfy (KYC)",
                required=True,
                env_var="IDENFY_API_KEY",
                status="not_configured",
                docs_url="https://sardis.sh/docs/setup#kyc",
            ),
            ProviderConfig(
                name="Coinbase (Onramp)",
                required=False,
                env_var="COINBASE_PROJECT_ID",
                status="optional",
                docs_url="https://sardis.sh/docs/setup#onramp",
            ),
        ],
        env_vars={
            "SARDIS_ENV": "production",
            "SARDIS_CHAIN": "base",
            "SARDIS_AGIT_FAIL_OPEN": "false",
            "SARDIS_WEBHOOK_SIGNATURES": "true",
        },
        policy_defaults="Max $1,000 per transaction. Daily limit $5,000. Require approval above $500. Multi-sig above $2,000. Block gambling and adult MCCs.",
        safety_defaults={
            "kill_switch": "armed",
            "auto_freeze": True,
            "webhook_signatures": True,
            "rate_limiting": True,
        },
        recommended_for=["production", "enterprise", "design-partner-pilot"],
    ),
]

_TEMPLATES_BY_ID: dict[str, EnvironmentTemplate] = {t.id: t for t in TEMPLATES}


@router.get("/", response_model=list[EnvironmentTemplate])
async def list_environment_templates() -> list[EnvironmentTemplate]:
    """List all pre-built environment templates."""
    return TEMPLATES


@router.get("/{template_id}", response_model=EnvironmentTemplate)
async def get_environment_template(template_id: str) -> EnvironmentTemplate:
    """Get a single environment template by ID."""
    template = _TEMPLATES_BY_ID.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return template
