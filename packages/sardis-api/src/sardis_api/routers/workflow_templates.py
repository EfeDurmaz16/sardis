"""Workflow templates for design partner onboarding.

Pre-built, opinionated configurations for common pilot workflows.
Each template includes policy defaults, approval settings, and setup guidance.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class WorkflowTemplate(BaseModel):
    id: str
    name: str
    description: str
    category: str  # "procurement", "travel", "agent-to-agent"
    policy_text: str  # Natural language policy to apply
    approval_config: dict  # Approval workflow defaults
    evidence_expectations: list[str]  # What evidence to collect
    setup_steps: list[str]  # Step-by-step setup guide
    assumptions: list[str]  # What the template assumes about the user's setup


TEMPLATES = [
    WorkflowTemplate(
        id="procurement-api",
        name="API Procurement",
        description="AI agent purchases API credits, cloud compute, and SaaS subscriptions. Common for dev teams automating infrastructure spending.",
        category="procurement",
        policy_text="Max $500 per transaction. Daily limit $2,000. Only allow payments to: OpenAI, Anthropic, AWS, Google Cloud, Azure, Vercel, GitHub, Cloudflare. Require approval above $200.",
        approval_config={
            "require_approval_above": 200,
            "auto_approve_below": 50,
            "approval_timeout_hours": 4,
            "notify_channels": ["email", "slack"],
        },
        evidence_expectations=[
            "Policy decision for every transaction",
            "Approval record for transactions above $200",
            "Execution receipt with chain tx hash",
            "Monthly spend summary per merchant",
        ],
        setup_steps=[
            "Create an agent with name 'Procurement Agent'",
            "Create a wallet on Base chain",
            "Apply the procurement policy template",
            "Set up a webhook for payment notifications",
            "Fund the wallet with USDC (recommended: $500 for testing)",
            "Configure Slack notifications for approvals",
        ],
        assumptions=[
            "Agent purchases API credits on behalf of the team",
            "Finance team reviews transactions above $200",
            "All payments are in USDC on Base chain",
            "Merchant allowlist is pre-configured",
        ],
    ),
    WorkflowTemplate(
        id="travel-expense",
        name="Travel & Expense",
        description="AI agent manages travel bookings and expense approvals. Virtual cards issued per trip with spending controls.",
        category="travel",
        policy_text="Max $1,000 per transaction. Daily limit $3,000. Block gambling and adult entertainment MCCs. Require approval for hotels above $300/night. Virtual card per trip.",
        approval_config={
            "require_approval_above": 500,
            "auto_approve_below": 100,
            "approval_timeout_hours": 8,
            "notify_channels": ["email", "slack"],
            "multi_sig_above": 2000,
        },
        evidence_expectations=[
            "Policy decision for every transaction",
            "Virtual card issuance record per trip",
            "Approval chain for high-value bookings",
            "Trip-level spend aggregation",
            "MCC category verification",
        ],
        setup_steps=[
            "Create an agent with name 'Travel Agent'",
            "Create a wallet on Base chain",
            "Apply the travel & expense policy template",
            "Issue a virtual card for the agent",
            "Configure MCC blocking (gambling, adult)",
            "Set up approval workflow for managers",
            "Fund the wallet with USDC (recommended: $2,000 for testing)",
        ],
        assumptions=[
            "One virtual card per trip or per agent",
            "Manager approval for bookings above $500",
            "Multi-signature for expenses above $2,000",
            "Blocked MCC categories enforced at card level",
        ],
    ),
    WorkflowTemplate(
        id="agent-escrow",
        name="Agent-to-Agent Escrow",
        description="Two AI agents exchange services with escrow-protected payments. Payment held until service delivery is confirmed.",
        category="agent-to-agent",
        policy_text="Max $2,000 per escrow. Daily limit $5,000. Escrow timeout 24 hours. Auto-release on delivery confirmation. Dispute resolution via human arbiter.",
        approval_config={
            "require_approval_above": 1000,
            "auto_approve_below": 200,
            "approval_timeout_hours": 24,
            "notify_channels": ["webhook"],
            "escrow_enabled": True,
        },
        evidence_expectations=[
            "Escrow creation record",
            "Service delivery confirmation",
            "Escrow release or dispute record",
            "Both agents' policy decisions",
            "Arbiter decision (if disputed)",
        ],
        setup_steps=[
            "Create buyer agent and seller agent",
            "Create wallets for both agents on Base chain",
            "Apply escrow policy to buyer agent",
            "Register seller agent as trusted counterparty",
            "Configure webhook for escrow state changes",
            "Fund buyer wallet with USDC (recommended: $1,000 for testing)",
            "Test with a small escrow transaction",
        ],
        assumptions=[
            "Both agents are registered in Sardis",
            "Escrow uses on-chain smart contract",
            "Delivery confirmation via webhook or API call",
            "Human arbiter available for disputes",
        ],
    ),
]

_TEMPLATE_INDEX: dict[str, WorkflowTemplate] = {t.id: t for t in TEMPLATES}


@router.get("/", response_model=list[WorkflowTemplate])
async def list_templates():
    """List all available workflow templates."""
    return TEMPLATES


@router.get("/{template_id}", response_model=WorkflowTemplate)
async def get_template(template_id: str):
    """Get a specific workflow template by ID."""
    template = _TEMPLATE_INDEX.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return template
