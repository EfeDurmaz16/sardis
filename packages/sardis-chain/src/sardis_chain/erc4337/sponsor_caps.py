"""Staged sponsor-cap enforcement for ERC-4337 paymaster sponsorship."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .user_operation import UserOperation


@dataclass(frozen=True)
class StageCaps:
    per_op_wei: int
    daily_wei: int


DEFAULT_STAGE_CAPS: dict[str, StageCaps] = {
    "pilot": StageCaps(per_op_wei=5_000_000_000_000_000, daily_wei=50_000_000_000_000_000),
    "beta": StageCaps(per_op_wei=20_000_000_000_000_000, daily_wei=200_000_000_000_000_000),
    "ga": StageCaps(per_op_wei=50_000_000_000_000_000, daily_wei=500_000_000_000_000_000),
}


class SponsorCapExceeded(RuntimeError):
    """Raised when sponsorship would exceed configured rollout caps."""


class SponsorCapGuard:
    """In-process staged cap guard for sponsored ERC-4337 operations."""

    def __init__(self, stage: str = "pilot", stage_caps_json: str = ""):
        normalized_stage = (stage or "pilot").strip().lower()
        self._stage = normalized_stage if normalized_stage in DEFAULT_STAGE_CAPS else "pilot"
        self._caps = self._load_caps(stage_caps_json)
        self._daily_usage_wei: dict[tuple[str, str], int] = {}

    @property
    def stage(self) -> str:
        return self._stage

    def _load_caps(self, stage_caps_json: str) -> dict[str, StageCaps]:
        caps: dict[str, StageCaps] = dict(DEFAULT_STAGE_CAPS)
        raw = (stage_caps_json or "").strip()
        if not raw:
            return caps

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return caps

        if not isinstance(parsed, dict):
            return caps

        for stage, values in parsed.items():
            if not isinstance(stage, str) or stage not in DEFAULT_STAGE_CAPS:
                continue
            if not isinstance(values, dict):
                continue
            try:
                per_op = int(values.get("per_op_wei", caps[stage].per_op_wei))
                daily = int(values.get("daily_wei", caps[stage].daily_wei))
            except (TypeError, ValueError):
                continue
            if per_op > 0 and daily > 0:
                caps[stage] = StageCaps(per_op_wei=per_op, daily_wei=daily)

        return caps

    def current_caps(self) -> StageCaps:
        return self._caps[self._stage]

    @staticmethod
    def estimate_max_cost_wei(user_op: UserOperation) -> int:
        gas_total = int(user_op.call_gas_limit) + int(user_op.verification_gas_limit) + int(user_op.pre_verification_gas)
        return max(0, gas_total * int(user_op.max_fee_per_gas))

    def reserve(self, chain: str, estimated_cost_wei: int) -> None:
        if estimated_cost_wei < 0:
            raise SponsorCapExceeded("negative_estimated_cost_not_allowed")

        caps = self.current_caps()
        if estimated_cost_wei > caps.per_op_wei:
            raise SponsorCapExceeded(
                f"erc4337_sponsor_per_op_cap_exceeded: estimated={estimated_cost_wei} cap={caps.per_op_wei} stage={self._stage}"
            )

        day_bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        usage_key = (chain, day_bucket)
        current = self._daily_usage_wei.get(usage_key, 0)
        projected = current + estimated_cost_wei
        if projected > caps.daily_wei:
            raise SponsorCapExceeded(
                f"erc4337_sponsor_daily_cap_exceeded: projected={projected} cap={caps.daily_wei} stage={self._stage} chain={chain}"
            )

        self._daily_usage_wei[usage_key] = projected

    def snapshot_usage(self) -> dict[str, Any]:
        return {
            "stage": self._stage,
            "caps": {
                "per_op_wei": self.current_caps().per_op_wei,
                "daily_wei": self.current_caps().daily_wei,
            },
            "daily_usage_wei": {
                f"{chain}:{day}": value for (chain, day), value in self._daily_usage_wei.items()
            },
        }

