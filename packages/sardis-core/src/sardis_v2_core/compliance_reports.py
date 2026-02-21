"""Compliance Report Generator for Sardis."""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from datetime import datetime, date
from uuid import uuid4
import hashlib
import json

class ReportType(Enum):
    MONTHLY_SPENDING = "monthly_spending"
    POLICY_COMPLIANCE = "policy_compliance"
    KYA_VERIFICATION = "kya_verification"
    AUDIT_TRAIL = "audit_trail"
    TAX_REPORT = "tax_report"

class ReportFormat(Enum):
    JSON = "json"
    CSV = "csv"
    HTML = "html"

@dataclass
class ReportConfig:
    report_type: ReportType
    date_from: date
    date_to: date
    org_id: str | None = None
    agent_ids: list[str] | None = None
    format: ReportFormat = ReportFormat.JSON

@dataclass
class ReportResult:
    id: str = field(default_factory=lambda: f"rpt_{uuid4().hex[:12]}")
    report_type: ReportType = ReportType.MONTHLY_SPENDING
    generated_at: datetime = field(default_factory=datetime.utcnow)
    config: ReportConfig | None = None
    data: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)

@dataclass
class ReportSchedule:
    id: str = field(default_factory=lambda: f"sched_{uuid4().hex[:12]}")
    report_type: ReportType = ReportType.MONTHLY_SPENDING
    frequency: str = "monthly"  # daily, weekly, monthly
    config: ReportConfig | None = None
    email_to: list[str] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_run: datetime | None = None

class ComplianceReportGenerator:
    """Generate compliance reports from ledger and transaction data."""

    def __init__(self):
        self._reports: dict[str, ReportResult] = {}
        self._schedules: dict[str, ReportSchedule] = {}

    async def generate(self, config: ReportConfig) -> ReportResult:
        generators = {
            ReportType.MONTHLY_SPENDING: self._generate_monthly_spending,
            ReportType.POLICY_COMPLIANCE: self._generate_policy_compliance,
            ReportType.KYA_VERIFICATION: self._generate_kya_verification,
            ReportType.AUDIT_TRAIL: self._generate_audit_trail,
            ReportType.TAX_REPORT: self._generate_tax_report,
        }
        result = await generators[config.report_type](config)
        self._reports[result.id] = result
        return result

    async def _generate_monthly_spending(self, config: ReportConfig) -> ReportResult:
        # Demo data for spending report
        data = {
            "period": {"from": str(config.date_from), "to": str(config.date_to)},
            "total_spend": "47250.00",
            "currency": "USD",
            "agent_breakdown": [
                {"agent_id": "procurement-agent", "total": "25000.00", "tx_count": 45, "avg_tx": "555.56", "top_merchant": "AWS"},
                {"agent_id": "api-buyer-agent", "total": "15000.00", "tx_count": 120, "avg_tx": "125.00", "top_merchant": "OpenAI"},
                {"agent_id": "research-agent", "total": "7250.00", "tx_count": 30, "avg_tx": "241.67", "top_merchant": "Anthropic"},
            ],
            "team_breakdown": [
                {"team": "Engineering", "total": "32250.00", "agents": 2},
                {"team": "Research", "total": "15000.00", "agents": 1},
            ],
            "month_over_month": {"current": "47250.00", "previous": "42100.00", "change_pct": "12.2"},
            "top_merchants": [
                {"merchant": "AWS", "total": "18000.00", "category": "Cloud Infrastructure"},
                {"merchant": "OpenAI", "total": "12000.00", "category": "AI/ML APIs"},
                {"merchant": "Anthropic", "total": "7250.00", "category": "AI/ML APIs"},
                {"merchant": "GitHub", "total": "5000.00", "category": "Developer Tools"},
                {"merchant": "Vercel", "total": "5000.00", "category": "Cloud Infrastructure"},
            ],
        }
        summary = {
            "total_spend": "47250.00",
            "active_agents": 3,
            "total_transactions": 195,
            "avg_transaction": "242.31",
            "highest_spender": "procurement-agent",
            "month_over_month_change": "+12.2%",
        }
        return ReportResult(report_type=ReportType.MONTHLY_SPENDING, config=config, data=data, summary=summary)

    async def _generate_policy_compliance(self, config: ReportConfig) -> ReportResult:
        data = {
            "period": {"from": str(config.date_from), "to": str(config.date_to)},
            "total_transactions": 195,
            "approved": 187,
            "blocked": 8,
            "compliance_rate": "95.9%",
            "violations": [
                {"date": "2026-02-05", "agent": "procurement-agent", "amount": "5500.00", "reason": "Exceeded daily limit ($5000)", "policy": "daily_limit"},
                {"date": "2026-02-08", "agent": "api-buyer-agent", "amount": "200.00", "reason": "Merchant not in allowed list", "policy": "merchant_whitelist"},
                {"date": "2026-02-12", "agent": "procurement-agent", "amount": "3000.00", "reason": "Weekend spending disabled", "policy": "time_restriction"},
                {"date": "2026-02-14", "agent": "research-agent", "amount": "1500.00", "reason": "Category not allowed", "policy": "category_restriction"},
                {"date": "2026-02-15", "agent": "api-buyer-agent", "amount": "600.00", "reason": "Exceeded monthly limit", "policy": "monthly_limit"},
                {"date": "2026-02-16", "agent": "procurement-agent", "amount": "800.00", "reason": "Velocity limit exceeded (>10 tx/hour)", "policy": "velocity_limit"},
                {"date": "2026-02-18", "agent": "research-agent", "amount": "2000.00", "reason": "Exceeded daily limit ($1500)", "policy": "daily_limit"},
                {"date": "2026-02-19", "agent": "api-buyer-agent", "amount": "150.00", "reason": "KYA level insufficient", "policy": "kya_requirement"},
            ],
            "policy_effectiveness": [
                {"policy": "daily_limit", "blocks": 3, "false_positives": 0},
                {"policy": "merchant_whitelist", "blocks": 1, "false_positives": 0},
                {"policy": "time_restriction", "blocks": 1, "false_positives": 1},
                {"policy": "monthly_limit", "blocks": 1, "false_positives": 0},
                {"policy": "velocity_limit", "blocks": 1, "false_positives": 0},
                {"policy": "kya_requirement", "blocks": 1, "false_positives": 0},
            ],
        }
        summary = {"compliance_rate": "95.9%", "total_blocks": 8, "false_positive_rate": "12.5%", "most_common_violation": "daily_limit"}
        return ReportResult(report_type=ReportType.POLICY_COMPLIANCE, config=config, data=data, summary=summary)

    async def _generate_kya_verification(self, config: ReportConfig) -> ReportResult:
        data = {
            "agents": [
                {"agent_id": "procurement-agent", "kya_level": 2, "status": "verified", "verified_at": "2026-01-15", "expires_at": "2027-01-15", "owner": "Acme Corp"},
                {"agent_id": "api-buyer-agent", "kya_level": 1, "status": "verified", "verified_at": "2026-02-01", "expires_at": "2027-02-01", "owner": "Acme Corp"},
                {"agent_id": "research-agent", "kya_level": 2, "status": "verified", "verified_at": "2026-01-20", "expires_at": "2027-01-20", "owner": "Research Lab Inc"},
            ],
            "kya_distribution": {"level_0": 0, "level_1": 1, "level_2": 2, "level_3": 0},
            "expiring_soon": [],
            "unverified": [],
        }
        summary = {"total_agents": 3, "verified": 3, "unverified": 0, "expiring_30d": 0, "avg_kya_level": 1.67}
        return ReportResult(report_type=ReportType.KYA_VERIFICATION, config=config, data=data, summary=summary)

    async def _generate_audit_trail(self, config: ReportConfig) -> ReportResult:
        entries = []
        prev_hash = "0" * 64
        for i in range(10):
            entry_data = {"index": i, "action": "payment_executed" if i % 2 == 0 else "policy_checked", "agent_id": f"agent-{i%3}", "amount": str(Decimal("100.00") * (i + 1)), "timestamp": f"2026-02-{10+i:02d}T12:00:00Z"}
            entry_json = json.dumps(entry_data, sort_keys=True)
            entry_hash = hashlib.sha256(f"{prev_hash}{entry_json}".encode()).hexdigest()
            entries.append({**entry_data, "previous_hash": prev_hash, "entry_hash": entry_hash})
            prev_hash = entry_hash
        data = {"entries": entries, "chain_valid": True, "entry_count": len(entries), "first_hash": entries[0]["entry_hash"], "last_hash": entries[-1]["entry_hash"]}
        summary = {"total_entries": 10, "chain_integrity": "valid", "period_start": str(config.date_from), "period_end": str(config.date_to)}
        return ReportResult(report_type=ReportType.AUDIT_TRAIL, config=config, data=data, summary=summary)

    async def _generate_tax_report(self, config: ReportConfig) -> ReportResult:
        data = {
            "period": {"from": str(config.date_from), "to": str(config.date_to)},
            "total_deductible": "42000.00",
            "total_non_deductible": "5250.00",
            "categories": [
                {"category": "Cloud Infrastructure", "total": "23000.00", "deductible": True, "tax_code": "5734"},
                {"category": "AI/ML APIs", "total": "19250.00", "deductible": True, "tax_code": "7372"},
                {"category": "Developer Tools", "total": "5000.00", "deductible": True, "tax_code": "7372"},
                {"category": "Office Supplies", "total": "3250.00", "deductible": True, "tax_code": "5943"},
                {"category": "Entertainment", "total": "2000.00", "deductible": False, "tax_code": "7941"},
            ],
            "by_jurisdiction": [
                {"jurisdiction": "US-CA", "total": "30000.00", "tax_rate": "8.75%"},
                {"jurisdiction": "US-NY", "total": "12000.00", "tax_rate": "8.875%"},
                {"jurisdiction": "EU-DE", "total": "5250.00", "tax_rate": "19%"},
            ],
        }
        summary = {"total_spend": "47250.00", "deductible": "42000.00", "non_deductible": "5250.00", "deductible_rate": "88.9%"}
        return ReportResult(report_type=ReportType.TAX_REPORT, config=config, data=data, summary=summary)

    def export_csv(self, result: ReportResult) -> str:
        if result.report_type == ReportType.MONTHLY_SPENDING:
            lines = ["Agent,Total Spend,Transactions,Avg Transaction,Top Merchant"]
            for agent in result.data.get("agent_breakdown", []):
                lines.append(f"{agent['agent_id']},{agent['total']},{agent['tx_count']},{agent['avg_tx']},{agent['top_merchant']}")
            return "\n".join(lines)
        elif result.report_type == ReportType.POLICY_COMPLIANCE:
            lines = ["Date,Agent,Amount,Reason,Policy"]
            for v in result.data.get("violations", []):
                lines.append(f"{v['date']},{v['agent']},{v['amount']},{v['reason']},{v['policy']}")
            return "\n".join(lines)
        elif result.report_type == ReportType.TAX_REPORT:
            lines = ["Category,Total,Deductible,Tax Code"]
            for c in result.data.get("categories", []):
                lines.append(f"{c['category']},{c['total']},{c['deductible']},{c['tax_code']}")
            return "\n".join(lines)
        return json.dumps(result.data, indent=2)

    def export_html(self, result: ReportResult) -> str:
        from .report_templates import get_html_template
        return get_html_template(result)

    @staticmethod
    def verify_audit_chain(entries: list[dict]) -> bool:
        if not entries:
            return True
        for i, entry in enumerate(entries):
            prev_hash = entries[i-1]["entry_hash"] if i > 0 else "0" * 64
            entry_data = {k: v for k, v in entry.items() if k not in ("previous_hash", "entry_hash")}
            entry_json = json.dumps(entry_data, sort_keys=True)
            expected = hashlib.sha256(f"{prev_hash}{entry_json}".encode()).hexdigest()
            if entry["entry_hash"] != expected:
                return False
            if entry["previous_hash"] != prev_hash:
                return False
        return True

    def get_report(self, report_id: str) -> ReportResult | None:
        return self._reports.get(report_id)

    def list_reports(self) -> list[ReportResult]:
        return list(self._reports.values())

    def create_schedule(self, schedule: ReportSchedule) -> ReportSchedule:
        self._schedules[schedule.id] = schedule
        return schedule

    def get_schedules(self) -> list[ReportSchedule]:
        return list(self._schedules.values())

    def delete_schedule(self, schedule_id: str) -> bool:
        return self._schedules.pop(schedule_id, None) is not None
