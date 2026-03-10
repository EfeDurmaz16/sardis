"""Policy analytics API for live feedback and deterministic tuning guidance."""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])


class OutcomeSummaryResponse(BaseModel):
    total_checks: int = 0
    allowed: int = 0
    denied: int = 0
    escalated: int = 0
    allow_rate: float = 0.0
    deny_rate: float = 0.0
    escalation_rate: float = 0.0


class DailyOutcomeResponse(BaseModel):
    date: str
    allowed: int = 0
    denied: int = 0
    escalated: int = 0


class DenyReasonResponse(BaseModel):
    reason: str
    count: int
    pct_of_denials: float
    trend: str


class PolicyVersionImpactResponse(BaseModel):
    version: str
    policy_version_id: str
    agent_id: str
    deployed_at: str
    label: str
    deny_rate_before: float = 0.0
    deny_rate_after: float = 0.0
    escalation_rate_before: float = 0.0
    escalation_rate_after: float = 0.0


class TuningSuggestionResponse(BaseModel):
    id: str
    severity: str
    title: str
    body: str
    action_label: str | None = None


class OutcomesAnalyticsResponse(BaseModel):
    summary_24h: OutcomeSummaryResponse
    summary_7d: OutcomeSummaryResponse
    summary_30d: OutcomeSummaryResponse
    daily_outcomes: list[DailyOutcomeResponse] = Field(default_factory=list)
    policy_versions: list[PolicyVersionImpactResponse] = Field(default_factory=list)


def _normalize_verdict(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"approved", "allow", "allowed", "ok"}:
        return "allowed"
    if normalized in {"escalated", "requires_approval"}:
        return "escalated"
    return "denied"


def _extract_reason(steps: Any, verdict: str) -> str:
    if not isinstance(steps, list):
        return "unknown"

    for raw_step in steps:
        if not isinstance(raw_step, dict):
            continue
        details = raw_step.get("details")
        details_dict = details if isinstance(details, dict) else {}

        if verdict == "escalated" and details_dict.get("requires_approval"):
            return "requires_approval"

        if raw_step.get("passed", True) is False:
            reason = details_dict.get("reason") or details_dict.get("error")
            if reason:
                return str(reason)
            step_name = raw_step.get("step_name")
            if step_name:
                return str(step_name)

    if verdict == "escalated":
        return "requires_approval"
    return verdict


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100, 1)


def _build_summary(decisions: list[dict[str, Any]], since: datetime) -> OutcomeSummaryResponse:
    filtered = [item for item in decisions if item["created_at"] >= since]
    total = len(filtered)
    allowed = sum(1 for item in filtered if item["verdict"] == "allowed")
    denied = sum(1 for item in filtered if item["verdict"] == "denied")
    escalated = sum(1 for item in filtered if item["verdict"] == "escalated")
    return OutcomeSummaryResponse(
        total_checks=total,
        allowed=allowed,
        denied=denied,
        escalated=escalated,
        allow_rate=_pct(allowed, total),
        deny_rate=_pct(denied, total),
        escalation_rate=_pct(escalated, total),
    )


def _build_daily_outcomes(decisions: list[dict[str, Any]], days: int = 30) -> list[DailyOutcomeResponse]:
    bucket: dict[str, Counter[str]] = defaultdict(Counter)
    today = datetime.now(UTC).date()

    for item in decisions:
        day = item["created_at"].date()
        if day < today - timedelta(days=days - 1):
            continue
        key = day.isoformat()
        bucket[key][item["verdict"]] += 1

    rows: list[DailyOutcomeResponse] = []
    for offset in range(days):
        day = today - timedelta(days=days - 1 - offset)
        key = day.isoformat()
        counts = bucket.get(key, Counter())
        rows.append(
            DailyOutcomeResponse(
                date=day.strftime("%b %d"),
                allowed=counts.get("allowed", 0),
                denied=counts.get("denied", 0),
                escalated=counts.get("escalated", 0),
            )
        )
    return rows


def _build_deny_reason_rows(decisions: list[dict[str, Any]]) -> list[DenyReasonResponse]:
    recent_cutoff = datetime.now(UTC) - timedelta(days=7)
    previous_cutoff = datetime.now(UTC) - timedelta(days=14)

    recent_counts: Counter[str] = Counter()
    previous_counts: Counter[str] = Counter()
    total_denials = 0

    for item in decisions:
        if item["verdict"] not in {"denied", "escalated"}:
            continue
        reason = item["reason"]
        if item["created_at"] >= recent_cutoff:
            recent_counts[reason] += 1
        elif item["created_at"] >= previous_cutoff:
            previous_counts[reason] += 1
        total_denials += 1

    rows: list[DenyReasonResponse] = []
    for reason, count in recent_counts.most_common(8):
        previous = previous_counts.get(reason, 0)
        if count > previous:
            trend = "up"
        elif count < previous:
            trend = "down"
        else:
            trend = "flat"
        rows.append(
            DenyReasonResponse(
                reason=reason,
                count=count,
                pct_of_denials=round((count / total_denials) * 100, 1) if total_denials else 0.0,
                trend=trend,
            )
        )
    return rows


def _build_policy_version_rows(
    versions: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> list[PolicyVersionImpactResponse]:
    rows: list[PolicyVersionImpactResponse] = []

    by_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in decisions:
        by_agent[item["agent_id"]].append(item)

    for item in versions:
        created_at = item["created_at"]
        agent_id = item["agent_id"]
        relevant = by_agent.get(agent_id, [])

        before = [
            decision
            for decision in relevant
            if created_at - timedelta(days=7) <= decision["created_at"] < created_at
        ]
        after = [
            decision
            for decision in relevant
            if created_at <= decision["created_at"] < created_at + timedelta(days=7)
        ]

        before_total = len(before)
        after_total = len(after)
        before_denied = sum(1 for decision in before if decision["verdict"] == "denied")
        after_denied = sum(1 for decision in after if decision["verdict"] == "denied")
        before_escalated = sum(1 for decision in before if decision["verdict"] == "escalated")
        after_escalated = sum(1 for decision in after if decision["verdict"] == "escalated")

        label = str(item.get("policy_text") or "").strip().replace("\n", " ")
        if label:
            label = label[:80]
        else:
            label = f"Policy v{item['version']}"

        rows.append(
            PolicyVersionImpactResponse(
                version=f"v{item['version']}",
                policy_version_id=item["id"],
                agent_id=agent_id,
                deployed_at=created_at.isoformat(),
                label=label,
                deny_rate_before=_pct(before_denied, before_total),
                deny_rate_after=_pct(after_denied, after_total),
                escalation_rate_before=_pct(before_escalated, before_total),
                escalation_rate_after=_pct(after_escalated, after_total),
            )
        )

    return rows


def _build_suggestions(
    summary_7d: OutcomeSummaryResponse,
    deny_reasons: list[DenyReasonResponse],
    version_rows: list[PolicyVersionImpactResponse],
) -> list[TuningSuggestionResponse]:
    suggestions: list[TuningSuggestionResponse] = []

    if deny_reasons:
        top_reason = deny_reasons[0]
        suggestions.append(
            TuningSuggestionResponse(
                id=f"review-{top_reason.reason}",
                severity="action" if top_reason.count >= 5 else "warn",
                title=f'"{top_reason.reason}" blocked {top_reason.count} checks recently',
                body=(
                    "This is the most common friction point in the last 7 days. "
                    "Review the policy rule behind it before operators start bypassing the control plane manually."
                ),
                action_label="Review policy rules",
            )
        )

    if summary_7d.total_checks > 0 and summary_7d.escalation_rate >= 10:
        suggestions.append(
            TuningSuggestionResponse(
                id="escalation-hotspot",
                severity="warn",
                title=f"Escalation rate is {summary_7d.escalation_rate:.1f}% over 7 days",
                body=(
                    "A high approval-required rate usually means the threshold is catching routine spend, "
                    "not just exceptional cases. Tighten routing or raise the threshold only if the evidence supports it."
                ),
                action_label="Inspect approval threshold",
            )
        )

    if version_rows:
        latest = version_rows[0]
        if latest.deny_rate_after < latest.deny_rate_before:
            suggestions.append(
                TuningSuggestionResponse(
                    id="latest-version-improved",
                    severity="info",
                    title=f"{latest.version} reduced deny rate after deployment",
                    body=(
                        "The latest policy version appears to have lowered policy friction. "
                        "Use the version history and scenario testing to confirm the change was intentional before broadening it."
                    ),
                    action_label="Compare versions",
                )
            )

    if not suggestions:
        suggestions.append(
            TuningSuggestionResponse(
                id="not-enough-signal",
                severity="info",
                title="Not enough live signal yet",
                body=(
                    "Policy outcomes are being tracked, but there is not enough recent activity to recommend a change. "
                    "Keep collecting real checks before editing thresholds or allowlists."
                ),
            )
        )

    return suggestions[:4]


async def _load_recent_decisions(org_id: str) -> list[dict[str, Any]]:
    from sardis_v2_core.database import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT pd.agent_id, pd.verdict, pd.steps_json, pd.created_at
            FROM policy_decisions pd
            JOIN agents a ON a.id = pd.agent_id
            WHERE a.owner_id = $1
              AND pd.created_at >= now() - interval '30 days'
            ORDER BY pd.created_at ASC
            """,
            org_id,
        )

    decisions: list[dict[str, Any]] = []
    for row in rows:
        verdict = _normalize_verdict(row["verdict"])
        steps = row["steps_json"]
        decisions.append(
            {
                "agent_id": row["agent_id"],
                "verdict": verdict,
                "reason": _extract_reason(steps, verdict),
                "created_at": row["created_at"],
            }
        )
    return decisions


async def _load_recent_versions(org_id: str) -> list[dict[str, Any]]:
    from sardis_v2_core.database import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT pv.id, pv.agent_id, pv.version, pv.policy_text, pv.created_at
            FROM policy_versions pv
            JOIN agents a ON a.id = pv.agent_id
            WHERE a.owner_id = $1
            ORDER BY pv.created_at DESC
            LIMIT 6
            """,
            org_id,
        )
    return [dict(row) for row in rows]


@router.get("/outcomes", response_model=OutcomesAnalyticsResponse)
async def get_policy_outcomes(
    period: str | None = Query(default=None),
    principal: Principal = Depends(require_principal),
) -> OutcomesAnalyticsResponse:
    del period  # Page receives all supported windows in a single response.

    decisions = await _load_recent_decisions(principal.organization_id)
    versions = await _load_recent_versions(principal.organization_id)
    now = datetime.now(UTC)

    return OutcomesAnalyticsResponse(
        summary_24h=_build_summary(decisions, now - timedelta(hours=24)),
        summary_7d=_build_summary(decisions, now - timedelta(days=7)),
        summary_30d=_build_summary(decisions, now - timedelta(days=30)),
        daily_outcomes=_build_daily_outcomes(decisions),
        policy_versions=_build_policy_version_rows(versions, decisions),
    )


@router.get("/deny-reasons", response_model=list[DenyReasonResponse])
async def get_policy_deny_reasons(
    principal: Principal = Depends(require_principal),
) -> list[DenyReasonResponse]:
    decisions = await _load_recent_decisions(principal.organization_id)
    return _build_deny_reason_rows(decisions)


@router.get("/suggestions", response_model=list[TuningSuggestionResponse])
async def get_policy_tuning_suggestions(
    principal: Principal = Depends(require_principal),
) -> list[TuningSuggestionResponse]:
    decisions = await _load_recent_decisions(principal.organization_id)
    versions = await _load_recent_versions(principal.organization_id)
    summary_7d = _build_summary(decisions, datetime.now(UTC) - timedelta(days=7))
    deny_reasons = _build_deny_reason_rows(decisions)
    version_rows = _build_policy_version_rows(versions, decisions)
    return _build_suggestions(summary_7d, deny_reasons, version_rows)
