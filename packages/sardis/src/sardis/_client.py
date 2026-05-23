"""Stub shells for ``Sardis`` and ``AsyncSardis``.

These are intentionally non-functional during the scaffold phase.
The full implementation lands during per-submodule consolidation; see
``project-directions/sardis-python-sdk-redesign.md`` (section "Main client").
"""
from __future__ import annotations

from typing import Any, Mapping

from sardis._version import __version__

__all__ = ["Sardis", "AsyncSardis"]


class _NotImplementedYet(RuntimeError):
    """Raised when the v2 client shell is invoked before consolidation lands."""


class Sardis:
    """Synchronous Sardis client (shell — not yet implemented).

    Example (post-migration):
        from sardis import Sardis

        client = Sardis(api_key="sk_live_...")
        wallet = client.wallets.create(name="agent-1", chain="base")
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.sardis.sh",
        timeout: float = 30.0,
        max_retries: int = 3,
        default_headers: Mapping[str, str] | None = None,
        http_client: Any | None = None,
        environment: str = "production",
    ) -> None:
        raise _NotImplementedYet(
            f"sardis {__version__} is a scaffold release. "
            "Use sardis-sdk (legacy) until consolidation completes."
        )

    def close(self) -> None: ...
    def __enter__(self) -> "Sardis": return self
    def __exit__(self, *exc: Any) -> None: self.close()


class AsyncSardis:
    """Async-native counterpart to :class:`Sardis` (shell — not yet implemented)."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.sardis.sh",
        timeout: float = 30.0,
        max_retries: int = 3,
        default_headers: Mapping[str, str] | None = None,
        http_client: Any | None = None,
        environment: str = "production",
    ) -> None:
        raise _NotImplementedYet(
            f"sardis {__version__} is a scaffold release. "
            "Use sardis-sdk (legacy) until consolidation completes."
        )

    async def close(self) -> None: ...
    async def __aenter__(self) -> "AsyncSardis": return self
    async def __aexit__(self, *exc: Any) -> None: await self.close()
