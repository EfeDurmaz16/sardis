"""
Sardis OpenClaw — Open-source agent skill definitions.

Exports structured SkillDefinition dataclasses from the package README.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SkillDefinition:
    """A structured agent skill definition."""
    name: str
    description: str
    category: str
    parameters: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    version: str = "0.1.0"


# Core skill definitions
SKILLS: List[SkillDefinition] = [
    SkillDefinition(
        name="balance_check",
        description="Check wallet balance across supported chains",
        category="wallet",
        parameters=["wallet_id", "chain"],
        required_permissions=["wallet:read"],
    ),
    SkillDefinition(
        name="send_payment",
        description="Send a stablecoin payment via mandate",
        category="payment",
        parameters=["recipient", "amount", "currency", "chain"],
        required_permissions=["wallet:write", "mandate:create"],
    ),
    SkillDefinition(
        name="check_compliance",
        description="Run compliance preflight on a transaction",
        category="compliance",
        parameters=["recipient_address", "amount"],
        required_permissions=["compliance:read"],
    ),
    SkillDefinition(
        name="create_invoice",
        description="Create a payment invoice for incoming funds",
        category="invoicing",
        parameters=["amount", "currency", "description"],
        required_permissions=["invoice:create"],
    ),
    SkillDefinition(
        name="bridge_transfer",
        description="Bridge stablecoins between supported chains via CCTP",
        category="bridge",
        parameters=["source_chain", "dest_chain", "amount", "token"],
        required_permissions=["wallet:write", "bridge:execute"],
    ),
    SkillDefinition(
        name="spending_report",
        description="Generate spending analytics report for an agent",
        category="analytics",
        parameters=["agent_id", "period_days"],
        required_permissions=["analytics:read"],
    ),
    SkillDefinition(
        name="policy_update",
        description="Update spending policy for an agent wallet",
        category="policy",
        parameters=["agent_id", "policy_rules"],
        required_permissions=["policy:write"],
    ),
]


def get_skill(name: str) -> Optional[SkillDefinition]:
    """Get a skill definition by name."""
    for skill in SKILLS:
        if skill.name == name:
            return skill
    return None


def list_skills(category: Optional[str] = None) -> List[SkillDefinition]:
    """List all skills, optionally filtered by category."""
    if category:
        return [s for s in SKILLS if s.category == category]
    return list(SKILLS)


from typing import Type

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult
from sardis_openclaw.skills import (
    BalanceCheckSkill,
    SendPaymentSkill,
    ComplianceCheckSkill,
    CreateInvoiceSkill,
    BridgeTransferSkill,
    SpendingReportSkill,
    PolicyUpdateSkill,
)

SKILL_REGISTRY: dict[str, Type[OpenClawSkill]] = {
    "balance_check": BalanceCheckSkill,
    "send_payment": SendPaymentSkill,
    "check_compliance": ComplianceCheckSkill,
    "create_invoice": CreateInvoiceSkill,
    "bridge_transfer": BridgeTransferSkill,
    "spending_report": SpendingReportSkill,
    "policy_update": PolicyUpdateSkill,
}


def get_executable_skill(name: str) -> OpenClawSkill:
    """Get an executable skill instance by name."""
    cls = SKILL_REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"Unknown skill: {name}. Available: {list(SKILL_REGISTRY.keys())}")
    return cls()


__all__ = [
    "SkillDefinition",
    "SKILLS",
    "get_skill",
    "list_skills",
    "OpenClawSkill",
    "SkillContext",
    "SkillResult",
    "BalanceCheckSkill",
    "SendPaymentSkill",
    "ComplianceCheckSkill",
    "CreateInvoiceSkill",
    "BridgeTransferSkill",
    "SpendingReportSkill",
    "PolicyUpdateSkill",
    "SKILL_REGISTRY",
    "get_executable_skill",
]
