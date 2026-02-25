"""JSON serialization helpers for SpendingPolicy.

We persist SpendingPolicy in JSONB fields (demo + production).
The schema is intentionally minimal and backwards-compatible.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from .spending_policy import MerchantRule, SpendingPolicy, SpendingScope, TimeWindowLimit, TrustLevel


def _dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _iso_to_dt(value: str) -> datetime:
    # datetime.fromisoformat supports offsets; fall back to UTC if missing
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def spending_policy_to_json(policy: SpendingPolicy) -> dict[str, Any]:
    def dec(v: Optional[Decimal]) -> Optional[str]:
        return str(v) if v is not None else None

    def twl(v: Optional[TimeWindowLimit]) -> Optional[dict[str, Any]]:
        if v is None:
            return None
        return {
            "window_type": v.window_type,
            "limit_amount": dec(v.limit_amount),
            "currency": v.currency,
            "current_spent": dec(v.current_spent),
            "window_start": _dt_to_iso(v.window_start),
        }

    def mr(v: MerchantRule) -> dict[str, Any]:
        return {
            "rule_id": v.rule_id,
            "rule_type": v.rule_type,
            "merchant_id": v.merchant_id,
            "category": v.category,
            "max_per_tx": dec(v.max_per_tx),
            "daily_limit": dec(v.daily_limit),
            "reason": v.reason,
            "created_at": _dt_to_iso(v.created_at),
            "expires_at": _dt_to_iso(v.expires_at) if v.expires_at else None,
        }

    return {
        "policy_id": policy.policy_id,
        "agent_id": policy.agent_id,
        "trust_level": policy.trust_level.value,
        "limit_per_tx": dec(policy.limit_per_tx),
        "limit_total": dec(policy.limit_total),
        "spent_total": dec(policy.spent_total),
        "daily_limit": twl(policy.daily_limit),
        "weekly_limit": twl(policy.weekly_limit),
        "monthly_limit": twl(policy.monthly_limit),
        "merchant_rules": [mr(r) for r in policy.merchant_rules],
        "allowed_scopes": [s.value for s in policy.allowed_scopes],
        "blocked_merchant_categories": list(policy.blocked_merchant_categories),
        "allowed_chains": list(policy.allowed_chains),
        "allowed_tokens": list(policy.allowed_tokens),
        "allowed_destination_addresses": list(policy.allowed_destination_addresses),
        "blocked_destination_addresses": list(policy.blocked_destination_addresses),
        "require_preauth": bool(policy.require_preauth),
        "max_hold_hours": int(policy.max_hold_hours),
        "created_at": _dt_to_iso(policy.created_at),
        "updated_at": _dt_to_iso(policy.updated_at),
    }


def spending_policy_from_json(data: dict[str, Any]) -> SpendingPolicy:
    def dec(v: Any, default: str = "0") -> Decimal:
        if v is None:
            return Decimal(default)
        return Decimal(str(v))

    def twl(v: Any) -> Optional[TimeWindowLimit]:
        if not isinstance(v, dict):
            return None
        return TimeWindowLimit(
            window_type=str(v.get("window_type", "daily")),
            limit_amount=dec(v.get("limit_amount", "0")),
            currency=str(v.get("currency", "USDC")),
            current_spent=dec(v.get("current_spent", "0")),
            window_start=_iso_to_dt(v.get("window_start", datetime.now(timezone.utc).isoformat())),
        )

    def mr(v: Any) -> MerchantRule:
        if not isinstance(v, dict):
            v = {}
        return MerchantRule(
            rule_id=str(v.get("rule_id") or ""),
            rule_type=str(v.get("rule_type") or "allow"),
            merchant_id=v.get("merchant_id"),
            category=v.get("category"),
            max_per_tx=Decimal(str(v["max_per_tx"])) if v.get("max_per_tx") is not None else None,
            daily_limit=Decimal(str(v["daily_limit"])) if v.get("daily_limit") is not None else None,
            reason=v.get("reason"),
            created_at=_iso_to_dt(v.get("created_at", datetime.now(timezone.utc).isoformat())),
            expires_at=_iso_to_dt(v["expires_at"]) if v.get("expires_at") else None,
        )

    trust_raw = str(data.get("trust_level", "low"))
    try:
        trust = TrustLevel(trust_raw)
    except Exception:
        trust = TrustLevel.LOW

    allowed_scopes: list[SpendingScope] = []
    for s in data.get("allowed_scopes", ["all"]) or ["all"]:
        try:
            allowed_scopes.append(SpendingScope(str(s)))
        except Exception:
            continue
    if not allowed_scopes:
        allowed_scopes = [SpendingScope.ALL]

    policy = SpendingPolicy(
        policy_id=str(data.get("policy_id") or ""),
        agent_id=str(data.get("agent_id") or ""),
        trust_level=trust,
        limit_per_tx=dec(data.get("limit_per_tx", "100.00"), default="100.00"),
        limit_total=dec(data.get("limit_total", "1000.00"), default="1000.00"),
        spent_total=dec(data.get("spent_total", "0"), default="0"),
        daily_limit=twl(data.get("daily_limit")),
        weekly_limit=twl(data.get("weekly_limit")),
        monthly_limit=twl(data.get("monthly_limit")),
        merchant_rules=[mr(r) for r in (data.get("merchant_rules") or [])],
        allowed_scopes=allowed_scopes,
        blocked_merchant_categories=[str(x).lower() for x in (data.get("blocked_merchant_categories") or [])],
        allowed_chains=[str(x).strip().lower() for x in (data.get("allowed_chains") or []) if str(x).strip()],
        allowed_tokens=[str(x).strip().upper() for x in (data.get("allowed_tokens") or []) if str(x).strip()],
        allowed_destination_addresses=[
            str(x).strip().lower() for x in (data.get("allowed_destination_addresses") or []) if str(x).strip()
        ],
        blocked_destination_addresses=[
            str(x).strip().lower() for x in (data.get("blocked_destination_addresses") or []) if str(x).strip()
        ],
        require_preauth=bool(data.get("require_preauth", False)),
        max_hold_hours=int(data.get("max_hold_hours", 168)),
        created_at=_iso_to_dt(data.get("created_at", datetime.now(timezone.utc).isoformat())),
        updated_at=_iso_to_dt(data.get("updated_at", datetime.now(timezone.utc).isoformat())),
    )
    return policy
