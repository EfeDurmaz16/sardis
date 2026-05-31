"""Provider registry: env -> client construction behind typed capability ports.

The registry is the single place that decides *which* implementation backs each
capability port.  It mirrors the fail-closed-in-production pattern of
``server.dependencies.build_moat_ports``:

* **Env-gated.** A real provider activates only when its credentials are set
  (resolved through the existing ``configure_*_runtime`` helpers so env logic is
  not duplicated).
* **Sandbox fallback (dev/test only).** When a capability's real provider is
  not configured, the registry returns a SANDBOX impl so the suite and local
  dev run green without live keys.
* **Fail-closed in production.** In production, if a *required* capability has
  no configured provider, asking for it raises rather than silently handing
  back a simulated impl on a money path.

The registry also owns the httpx lifecycle of the clients it constructs:
:meth:`aclose` closes every client it built.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any

from .adapters import (
    CircleCpnOfframpAdapter,
    ConduitOnrampAdapter,
    LithicFiatAccountAdapter,
    TurnkeyOnrampAdapter,
)
from .ports.capabilities import (
    CapabilityPort,
    FiatAccountPort,
    OfframpPort,
    OnrampPort,
)
from .ports.types import ProviderCapability, ProviderNotConfigured
from .sandbox import (
    SandboxBridgePort,
    SandboxCardPort,
    SandboxCustodyPort,
    SandboxFiatAccountPort,
    SandboxKycPort,
    SandboxKytPort,
    SandboxOfframpPort,
    SandboxOnrampPort,
    SandboxSwapPort,
)

logger = logging.getLogger(__name__)

# Capabilities the production money path treats as required.  Asking for one of
# these in production when no real provider is configured fails closed (no
# silent sandbox fallback on a money path).
_REQUIRED_IN_PRODUCTION: frozenset[ProviderCapability] = frozenset(
    {
        ProviderCapability.CUSTODY,
        ProviderCapability.KYT,
    }
)

# Sandbox impl per capability, used as the dev/test fallback.
_SANDBOX_FACTORIES = {
    ProviderCapability.CUSTODY: lambda: SandboxCustodyPort(provider="sandbox"),
    ProviderCapability.FIAT_ACCOUNT: lambda: SandboxFiatAccountPort(provider="sandbox"),
    ProviderCapability.ONRAMP: lambda: SandboxOnrampPort(provider="sandbox"),
    ProviderCapability.OFFRAMP: lambda: SandboxOfframpPort(provider="sandbox"),
    ProviderCapability.SWAP: lambda: SandboxSwapPort(provider="sandbox"),
    ProviderCapability.BRIDGE: lambda: SandboxBridgePort(provider="sandbox"),
    ProviderCapability.CARD: lambda: SandboxCardPort(provider="sandbox"),
    ProviderCapability.KYC: lambda: SandboxKycPort(provider="sandbox"),
    ProviderCapability.KYT: lambda: SandboxKytPort(provider="sandbox"),
}


class ProviderRegistry:
    """Resolves and caches one capability-port implementation per capability.

    Construct via :meth:`from_settings` (production / app wiring) which reads
    env through the existing ``configure_*_runtime`` helpers.  Tests can inject
    explicit adapters via the constructor to avoid touching the environment.
    """

    def __init__(
        self,
        *,
        is_production: bool,
        ports: Mapping[ProviderCapability, CapabilityPort] | None = None,
        owned_clients: list[Any] | None = None,
    ) -> None:
        self._is_production = is_production
        self._real: dict[ProviderCapability, CapabilityPort] = dict(ports or {})
        self._resolved: dict[ProviderCapability, CapabilityPort] = {}
        self._owned_clients: list[Any] = list(owned_clients or [])

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_settings(
        cls,
        settings: Any,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> ProviderRegistry:
        """Build a registry, wiring real adapters when credentials are present.

        Reuses ``configure_treasury_runtime`` / ``configure_cpn_runtime`` so the
        env-resolution + fail-closed-in-production logic lives in one place and
        cannot drift from the route-facing config.
        """
        from server.dependencies import (
            configure_cpn_runtime,
            configure_treasury_runtime,
        )

        env = environ if environ is not None else os.environ
        is_production = bool(getattr(settings, "is_production", False))
        ports: dict[ProviderCapability, CapabilityPort] = {}
        owned: list[Any] = []

        # --- Fiat account (Lithic) ------------------------------------
        storage_url = env.get("DATABASE_URL", "") or getattr(settings, "database_url", "") or ""
        use_postgres = storage_url.startswith(("postgresql://", "postgres://"))
        treasury = configure_treasury_runtime(
            settings,
            database_url=storage_url,
            use_postgres=use_postgres,
            environ=env,
        )
        if treasury.lithic_treasury_client is not None:
            adapter = LithicFiatAccountAdapter(treasury.lithic_treasury_client)
            ports[ProviderCapability.FIAT_ACCOUNT] = adapter
            owned.append(treasury.lithic_treasury_client)
            logger.info("ProviderRegistry: FIAT_ACCOUNT -> lithic")

        # --- Offramp (Circle CPN) -------------------------------------
        cpn = configure_cpn_runtime(settings, environ=env)
        if cpn.cpn_client is not None:
            adapter = CircleCpnOfframpAdapter(cpn.cpn_client, sandbox=not is_production)
            ports[ProviderCapability.OFFRAMP] = adapter
            owned.append(cpn.cpn_client)
            logger.info("ProviderRegistry: OFFRAMP -> circle_cpn")

        # --- Onramp (Conduit preferred, Turnkey native fallback) ------
        onramp = cls._build_onramp(settings, env=env, is_production=is_production, owned=owned)
        if onramp is not None:
            ports[ProviderCapability.ONRAMP] = onramp

        return cls(is_production=is_production, ports=ports, owned_clients=owned)

    @staticmethod
    def _build_onramp(
        settings: Any,
        *,
        env: Mapping[str, str],
        is_production: bool,
        owned: list[Any],
    ) -> OnrampPort | None:
        # Conduit (fiat -> USDC on Tempo) takes precedence when configured.
        # Read keys from the injected env (do not call get_conduit_service(),
        # which reads os.environ directly and would ignore a test-injected env).
        conduit_key = env.get("CONDUIT_API_KEY")
        conduit_secret = env.get("CONDUIT_API_SECRET")
        if conduit_key and conduit_secret:
            try:
                from server.services.conduit_onramp import ConduitOnrampService

                sandbox = env.get("CONDUIT_SANDBOX", "true").lower() in ("true", "1", "yes")
                conduit = ConduitOnrampService(
                    api_key=conduit_key,
                    api_secret=conduit_secret,
                    sandbox=sandbox,
                )
                owned.append(conduit)
                logger.info("ProviderRegistry: ONRAMP -> conduit")
                return ConduitOnrampAdapter(conduit)
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: conduit init failed: %s", exc)

        # Turnkey native onramp (Coinbase/MoonPay widget).
        api_key = env.get("TURNKEY_API_PUBLIC_KEY") or env.get("TURNKEY_API_KEY")
        api_private = env.get("TURNKEY_API_PRIVATE_KEY")
        org_id = env.get("TURNKEY_ORGANIZATION_ID")
        if api_key and api_private and org_id:
            try:
                from sardis.wallet.turnkey_client import TurnkeyClient

                from server.services.turnkey_onramp import TurnkeyOnrampService

                client = TurnkeyClient(
                    api_key=api_key,
                    api_private_key=api_private,
                    organization_id=org_id,
                )
                logger.info("ProviderRegistry: ONRAMP -> turnkey")
                return TurnkeyOnrampAdapter(
                    TurnkeyOnrampService(turnkey_client=client),
                    sandbox=not is_production,
                )
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: turnkey onramp init failed: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def get(self, capability: ProviderCapability) -> CapabilityPort:
        """Return the impl for ``capability``.

        Real impl when configured; sandbox impl when absent in non-production.
        Fail-closed in production for required capabilities.
        """
        if capability in self._resolved:
            return self._resolved[capability]

        impl = self._real.get(capability)
        if impl is None:
            if self._is_production and capability in _REQUIRED_IN_PRODUCTION:
                raise ProviderNotConfigured(
                    f"no provider configured for required capability {capability.value!r} "
                    "in production",
                    provider="none",
                    capability=capability,
                )
            if self._is_production:
                logger.warning(
                    "ProviderRegistry: %s not configured in production; "
                    "returning sandbox impl (non-money or optional capability)",
                    capability.value,
                )
            impl = _SANDBOX_FACTORIES[capability]()

        self._resolved[capability] = impl
        return impl

    def has_real(self, capability: ProviderCapability) -> bool:
        """True when a real (non-sandbox) provider backs ``capability``."""
        return capability in self._real

    # Typed convenience accessors (narrow the protocol for callers/IDEs).
    def fiat_account(self) -> FiatAccountPort:
        return self.get(ProviderCapability.FIAT_ACCOUNT)  # type: ignore[return-value]

    def onramp(self) -> OnrampPort:
        return self.get(ProviderCapability.ONRAMP)  # type: ignore[return-value]

    def offramp(self) -> OfframpPort:
        return self.get(ProviderCapability.OFFRAMP)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        """Close every httpx-backed client the registry constructed."""
        for client in self._owned_clients:
            close = getattr(client, "close", None) or getattr(client, "aclose", None)
            if close is None:
                continue
            try:
                result = close()
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                logger.warning("ProviderRegistry: error closing %r: %s", client, exc)
        self._owned_clients.clear()
