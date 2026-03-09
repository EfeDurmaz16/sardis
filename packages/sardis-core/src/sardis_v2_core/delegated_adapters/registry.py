"""Multi-provider adapter registry for delegated payment execution.

Dispatches to the correct adapter based on the credential's network field.
"""
from __future__ import annotations

import logging

from ..delegated_credential import CredentialNetwork
from ..delegated_executor import DelegatedExecutorPort

logger = logging.getLogger(__name__)


class DelegatedAdapterRegistry:
    """Registry that maps CredentialNetwork → DelegatedExecutorPort adapter.

    Used by DelegatedExecutionAdapter to dispatch to the correct provider.
    """

    def __init__(self) -> None:
        self._adapters: dict[CredentialNetwork, DelegatedExecutorPort] = {}

    def register(self, network: CredentialNetwork, adapter: DelegatedExecutorPort) -> None:
        """Register an adapter for a credential network."""
        if network in self._adapters:
            logger.warning(
                "Overwriting existing adapter for network=%s", network.value,
            )
        self._adapters[network] = adapter
        logger.info("Registered delegated adapter for network=%s", network.value)

    def get(self, network: CredentialNetwork) -> DelegatedExecutorPort:
        """Look up the adapter for a credential network.

        Raises KeyError if no adapter is registered for the network.
        """
        adapter = self._adapters.get(network)
        if adapter is None:
            raise KeyError(
                f"No delegated adapter registered for network={network.value}. "
                f"Available: {[n.value for n in self._adapters]}"
            )
        return adapter

    def available_networks(self) -> list[CredentialNetwork]:
        """Return list of networks with registered adapters."""
        return list(self._adapters.keys())

    async def health_check_all(self) -> dict[str, bool]:
        """Run health checks on all registered adapters."""
        results: dict[str, bool] = {}
        for network, adapter in self._adapters.items():
            try:
                results[network.value] = await adapter.check_health()
            except Exception as e:
                logger.warning("Health check failed for %s: %s", network.value, e)
                results[network.value] = False
        return results

    def __len__(self) -> int:
        return len(self._adapters)

    def __contains__(self, network: CredentialNetwork) -> bool:
        return network in self._adapters
