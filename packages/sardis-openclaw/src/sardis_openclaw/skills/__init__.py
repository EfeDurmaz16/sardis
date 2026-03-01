"""Executable OpenClaw skills for Sardis."""
from sardis_openclaw.skills.balance import BalanceCheckSkill
from sardis_openclaw.skills.payment import SendPaymentSkill
from sardis_openclaw.skills.compliance import ComplianceCheckSkill
from sardis_openclaw.skills.invoice import CreateInvoiceSkill
from sardis_openclaw.skills.bridge import BridgeTransferSkill
from sardis_openclaw.skills.report import SpendingReportSkill
from sardis_openclaw.skills.policy import PolicyUpdateSkill

ALL_SKILLS = [
    BalanceCheckSkill,
    SendPaymentSkill,
    ComplianceCheckSkill,
    CreateInvoiceSkill,
    BridgeTransferSkill,
    SpendingReportSkill,
    PolicyUpdateSkill,
]

__all__ = [
    "BalanceCheckSkill",
    "SendPaymentSkill",
    "ComplianceCheckSkill",
    "CreateInvoiceSkill",
    "BridgeTransferSkill",
    "SpendingReportSkill",
    "PolicyUpdateSkill",
    "ALL_SKILLS",
]
