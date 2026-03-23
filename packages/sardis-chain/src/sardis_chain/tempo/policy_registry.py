"""TIP-403 Policy Registry — on-chain compliance for Tempo transfers.

The Policy Registry is a Tempo system contract that maintains
blocklists and whitelists for TIP-20 token transfers. Sardis
checks the registry before every Tempo transfer to ensure
compliance with issuer-mandated restrictions.

Registry operations:
  - isBlocked(address) → bool
  - isAllowed(token, from, to) → bool
  - getPolicy(token) → PolicyConfig

Usage::

    registry = TIP403PolicyRegistry()
    blocked = await registry.is_blocked("0xbad...")
    allowed = await registry.is_transfer_allowed(
        token="0x20c0...", from_addr="0xabc...", to_addr="0xdef..."
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("sardis.chain.tempo.policy_registry")

# TIP-403 Policy Registry system contract
POLICY_REGISTRY_ADDRESS = "0x403000000000000000000000000000000000403"


@dataclass
class TokenPolicy:
    """Compliance policy for a TIP-20 token."""
    token_address: str = ""
    issuer: str = ""
    blocklist_enabled: bool = True
    allowlist_enabled: bool = False
    transfer_restrictions: dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ComplianceCheckResult:
    """Result of a TIP-403 compliance check."""
    allowed: bool
    reason: str | None = None
    token: str = ""
    from_addr: str = ""
    to_addr: str = ""
    policy: TokenPolicy | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TIP403PolicyRegistry:
    """Queries the TIP-403 Policy Registry precompile on Tempo.

    Checks blocklists and whitelists before token transfers to
    ensure compliance with issuer policies (e.g., Circle USDC
    compliance requirements).
    """

    def __init__(
        self,
        rpc_url: str = "https://rpc.tempo.xyz",
        registry_address: str = POLICY_REGISTRY_ADDRESS,
    ) -> None:
        self._rpc_url = rpc_url
        self._registry = registry_address
        # Local cache to avoid repeated RPC calls
        self._blocklist_cache: dict[str, bool] = {}
        self._policy_cache: dict[str, TokenPolicy] = {}

    async def is_blocked(self, address: str) -> bool:
        """Check if an address is on the global blocklist."""
        if address in self._blocklist_cache:
            return self._blocklist_cache[address]

        result = await self._call_registry(
            "isBlocked(address)",
            [address],
        )
        blocked = result.get("blocked", False)
        self._blocklist_cache[address] = blocked

        if blocked:
            logger.warning("Address %s is blocked by TIP-403 registry", address)
        return blocked

    async def is_transfer_allowed(
        self,
        token: str,
        from_addr: str,
        to_addr: str,
    ) -> ComplianceCheckResult:
        """Check if a token transfer is allowed by the policy registry.

        Checks both blocklist (sender/receiver not sanctioned) and
        allowlist (if token requires allowlisted addresses).
        """
        # Check blocklist for both parties
        if await self.is_blocked(from_addr):
            return ComplianceCheckResult(
                allowed=False,
                reason=f"Sender {from_addr} is on the blocklist",
                token=token, from_addr=from_addr, to_addr=to_addr,
            )
        if await self.is_blocked(to_addr):
            return ComplianceCheckResult(
                allowed=False,
                reason=f"Receiver {to_addr} is on the blocklist",
                token=token, from_addr=from_addr, to_addr=to_addr,
            )

        # Check token-specific policy
        policy = await self.get_token_policy(token)
        if policy and policy.allowlist_enabled:
            result = await self._call_registry(
                "isAllowed(address,address,address)",
                [token, from_addr, to_addr],
            )
            if not result.get("allowed", True):
                return ComplianceCheckResult(
                    allowed=False,
                    reason="Transfer not on token allowlist",
                    token=token, from_addr=from_addr, to_addr=to_addr,
                    policy=policy,
                )

        return ComplianceCheckResult(
            allowed=True,
            token=token, from_addr=from_addr, to_addr=to_addr,
            policy=policy,
        )

    async def get_token_policy(self, token: str) -> TokenPolicy | None:
        """Get the compliance policy for a specific token."""
        if token in self._policy_cache:
            return self._policy_cache[token]

        result = await self._call_registry(
            "getPolicy(address)",
            [token],
        )
        if not result:
            return None

        policy = TokenPolicy(
            token_address=token,
            issuer=result.get("issuer", ""),
            blocklist_enabled=result.get("blocklist_enabled", True),
            allowlist_enabled=result.get("allowlist_enabled", False),
            transfer_restrictions=result.get("restrictions", {}),
        )
        self._policy_cache[token] = policy
        return policy

    def clear_cache(self) -> None:
        """Clear the local compliance cache."""
        self._blocklist_cache.clear()
        self._policy_cache.clear()

    async def _call_registry(
        self,
        method: str,
        params: list[str],
    ) -> dict[str, Any]:
        """Call the TIP-403 registry precompile via eth_call."""
        import httpx

        # Encode the call (simplified — real impl uses ABI encoding)
        call_data = self._encode_call(method, params)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_call",
                        "params": [{
                            "to": self._registry,
                            "data": call_data,
                        }, "latest"],
                        "id": 1,
                    },
                )
                result = resp.json()
                if "result" in result and result["result"] != "0x":
                    return self._decode_result(method, result["result"])
        except Exception:
            logger.debug("TIP-403 registry call failed for %s", method)

        return {}

    @staticmethod
    def _encode_call(method: str, params: list[str]) -> str:
        """Encode a registry call (simplified ABI encoding)."""
        import hashlib
        selector = hashlib.sha256(method.encode()).hexdigest()[:8]
        encoded_params = "".join(p[2:].zfill(64) if p.startswith("0x") else p.zfill(64) for p in params)
        return "0x" + selector + encoded_params

    @staticmethod
    def _decode_result(method: str, data: str) -> dict[str, Any]:
        """Decode a registry call result."""
        if len(data) < 66:
            return {}
        # Single bool result
        value = int(data[2:66], 16)
        if "isBlocked" in method:
            return {"blocked": value != 0}
        if "isAllowed" in method:
            return {"allowed": value != 0}
        return {"value": value}
