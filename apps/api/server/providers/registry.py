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
    BridgePort,
    CapabilityPort,
    CardPort,
    FiatAccountPort,
    OfframpPort,
    OnrampPort,
    SwapPort,
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

        # --- Fiat accounts (Dakota / Increase) + offramp bank leg -----
        # Env-gated: each activates only when its key is set.  Existing
        # higher-priority providers (Lithic fiat account, Circle CPN offramp)
        # are not overridden; these fill the slot only when it is still empty.
        cls._build_fiat_accounts(env=env, ports=ports, owned=owned)

        # --- Offramp aggregators (Onramper / Transak Stream / Coinbase) ---
        # crypto->fiat conversion leg.  Env-gated; each fills the OFFRAMP slot
        # only when it is still empty (Circle CPN + Increase keep precedence).
        cls._build_offramp(env=env, is_production=is_production, ports=ports, owned=owned)

        # --- Swap (LI.FI / 0x v2 / Jupiter) ---------------------------
        # Same-chain / cross-token swap.  Env-gated; tried in order, first
        # configured wins.  Each captures its integrator-fee (revenue) param.
        cls._build_swap(env=env, is_production=is_production, ports=ports, owned=owned)

        # --- Bridge (Squid / CCTP v2) ---------------------------------
        # Cross-chain bridge (the Base/Solana -> Tempo pattern).  Env-gated;
        # tried in order, first configured wins.  Squid needs an integrator id;
        # CCTP is keyless/canonical and is opt-in via a flag so the dev default
        # stays the SIMULATED sandbox impl.
        cls._build_bridge(env=env, is_production=is_production, ports=ports, owned=owned)

        # --- Cards (Crossmint primary / Lithic / Stripe Issuing) ------
        # Virtual-card issuing.  Env-gated; tried in order, first configured
        # wins.  Crossmint Agentic Cards is the primary (non-custodial dual-key,
        # agent-bound single-use VCs); Lithic (own BIN) and Stripe Issuing are
        # fallbacks.  Card is NOT required-in-production, so when none is set the
        # registry falls back to the SIMULATED sandbox card (no money moves).
        cls._build_cards(env=env, is_production=is_production, ports=ports, owned=owned)

        return cls(is_production=is_production, ports=ports, owned_clients=owned)

    @staticmethod
    def _build_cards(
        *,
        env: Mapping[str, str],
        is_production: bool,
        ports: dict[ProviderCapability, CapabilityPort],
        owned: list[Any],
    ) -> None:
        # Card-issuing providers. Tried in order; first configured wins.
        if ProviderCapability.CARD in ports:
            return

        default_env = "production" if is_production else "sandbox"

        # Crossmint Agentic Cards (PRIMARY) — Rain-backed. Requires the
        # Crossmint platform key; the Rain key backs the concrete card surface.
        crossmint_key = env.get("CROSSMINT_API_KEY")
        if crossmint_key:
            try:
                from .cards import CrossmintCardAdapter, CrossmintCardClient, CrossmintConfig

                client = CrossmintCardClient(
                    CrossmintConfig(
                        api_key=crossmint_key,
                        rain_api_key=env.get("CROSSMINT_RAIN_API_KEY") or env.get("RAIN_API_KEY"),
                        environment=env.get("CROSSMINT_ENVIRONMENT", default_env),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.CARD] = CrossmintCardAdapter(client)
                logger.info("ProviderRegistry: CARD -> crossmint")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: crossmint card init failed: %s", exc)

        # Lithic (FALLBACK) — Sardis's own BIN.
        lithic_key = env.get("LITHIC_API_KEY")
        if lithic_key:
            try:
                from .cards import LithicCardAdapter, LithicCardClient, LithicCardConfig

                client = LithicCardClient(
                    LithicCardConfig(
                        api_key=lithic_key,
                        environment=env.get("LITHIC_ENVIRONMENT", default_env),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.CARD] = LithicCardAdapter(client)
                logger.info("ProviderRegistry: CARD -> lithic")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: lithic card init failed: %s", exc)

        # Stripe Issuing (FALLBACK).
        stripe_key = env.get("STRIPE_ISSUING_API_KEY") or env.get("STRIPE_SECRET_KEY")
        if stripe_key:
            try:
                from .cards import (
                    StripeIssuingCardAdapter,
                    StripeIssuingClient,
                    StripeIssuingConfig,
                )

                client = StripeIssuingClient(
                    StripeIssuingConfig(
                        api_key=stripe_key,
                        environment=env.get("STRIPE_ISSUING_ENVIRONMENT", default_env),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.CARD] = StripeIssuingCardAdapter(client)
                logger.info("ProviderRegistry: CARD -> stripe_issuing")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: stripe issuing card init failed: %s", exc)

    @staticmethod
    def _build_bridge(
        *,
        env: Mapping[str, str],
        is_production: bool,
        ports: dict[ProviderCapability, CapabilityPort],
        owned: list[Any],
    ) -> None:
        # Cross-chain bridge providers. Tried in order; first configured wins.
        if ProviderCapability.BRIDGE in ports:
            return

        def _flag(name: str) -> bool:
            return env.get(name, "").strip().lower() in ("true", "1", "yes")

        def _float(name: str, default: float) -> float:
            raw = env.get(name)
            if raw is None or raw.strip() == "":
                return default
            try:
                return float(raw)
            except ValueError:
                logger.warning("ProviderRegistry: invalid float env %s=%r", name, raw)
                return default

        # Squid — intent-based aggregation; live on Tempo day-one (pathUSD).
        # Requires an integrator id on every request.
        squid_integrator = env.get("SQUID_INTEGRATOR_ID")
        if squid_integrator:
            try:
                from .bridge import SquidBridgeAdapter, SquidClient, SquidConfig

                client = SquidClient(
                    SquidConfig(
                        integrator_id=squid_integrator,
                        environment=env.get(
                            "SQUID_ENVIRONMENT",
                            "production" if is_production else "staging",
                        ),
                        slippage_percent=_float("SQUID_SLIPPAGE_PERCENT", 1.0),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.BRIDGE] = SquidBridgeAdapter(client)
                logger.info("ProviderRegistry: BRIDGE -> squid")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: squid init failed: %s", exc)

        # CCTP v2 — canonical USDC burn/mint; keyless (Iris is public), so it
        # must be explicitly enabled to wire (otherwise the dev default stays
        # the SIMULATED sandbox impl).
        if _flag("CCTP_ENABLED"):
            try:
                from .bridge import CctpBridgeAdapter, CctpClient, CctpConfig

                client = CctpClient(
                    CctpConfig(
                        environment=env.get(
                            "CCTP_ENVIRONMENT",
                            "production" if is_production else "sandbox",
                        ),
                        fast=env.get("CCTP_FAST", "true").strip().lower()
                        in ("true", "1", "yes"),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.BRIDGE] = CctpBridgeAdapter(client)
                logger.info("ProviderRegistry: BRIDGE -> cctp")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: cctp init failed: %s", exc)

    @staticmethod
    def _build_swap(
        *,
        env: Mapping[str, str],
        is_production: bool,
        ports: dict[ProviderCapability, CapabilityPort],
        owned: list[Any],
    ) -> None:
        # Swap providers. Tried in order; first configured wins. LI.FI works
        # keyless (low rate limits) so it activates when LIFI_ENABLED is truthy
        # OR a key/fee is set; 0x requires a key; Jupiter works keyless via the
        # lite host but only wires when JUPITER_ENABLED/key is set so the
        # default dev fallback stays the SIMULATED sandbox impl.
        if ProviderCapability.SWAP in ports:
            return

        def _flag(name: str) -> bool:
            return env.get(name, "").strip().lower() in ("true", "1", "yes")

        def _int(name: str) -> int | None:
            raw = env.get(name)
            if raw is None or raw.strip() == "":
                return None
            try:
                return int(raw)
            except ValueError:
                logger.warning("ProviderRegistry: invalid int env %s=%r", name, raw)
                return None

        def _float(name: str) -> float | None:
            raw = env.get(name)
            if raw is None or raw.strip() == "":
                return None
            try:
                return float(raw)
            except ValueError:
                logger.warning("ProviderRegistry: invalid float env %s=%r", name, raw)
                return None

        # LI.FI — keyless-capable; wire when explicitly enabled, keyed, or a
        # default integrator fee is configured.
        lifi_key = env.get("LIFI_API_KEY")
        if lifi_key or _flag("LIFI_ENABLED") or _float("LIFI_FEE") is not None:
            try:
                from .swap import LifiClient, LifiConfig, LifiSwapAdapter

                client = LifiClient(
                    LifiConfig(
                        api_key=lifi_key,
                        environment=env.get(
                            "LIFI_ENVIRONMENT",
                            "production" if is_production else "staging",
                        ),
                        integrator=env.get("LIFI_INTEGRATOR", "sardis"),
                        fee=_float("LIFI_FEE"),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.SWAP] = LifiSwapAdapter(client)
                logger.info("ProviderRegistry: SWAP -> lifi")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: lifi init failed: %s", exc)

        # 0x Swap API v2 — requires an API key.
        zerox_key = env.get("ZEROX_API_KEY") or env.get("ZERO_EX_API_KEY")
        if zerox_key:
            try:
                from .swap import ZeroExClient, ZeroExConfig, ZeroExSwapAdapter

                client = ZeroExClient(
                    ZeroExConfig(
                        api_key=zerox_key,
                        environment=env.get(
                            "ZEROX_ENVIRONMENT",
                            "production" if is_production else "sandbox",
                        ),
                        swap_fee_bps=_int("ZEROX_SWAP_FEE_BPS"),
                        swap_fee_recipient=env.get("ZEROX_SWAP_FEE_RECIPIENT"),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.SWAP] = ZeroExSwapAdapter(client)
                logger.info("ProviderRegistry: SWAP -> zerox")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: zerox init failed: %s", exc)

        # Jupiter — keyless-capable (lite host); wire when enabled or keyed.
        jupiter_key = env.get("JUPITER_API_KEY")
        if jupiter_key or _flag("JUPITER_ENABLED"):
            try:
                from .swap import JupiterClient, JupiterConfig, JupiterSwapAdapter

                client = JupiterClient(
                    JupiterConfig(
                        api_key=jupiter_key,
                        environment=env.get(
                            "JUPITER_ENVIRONMENT",
                            "production" if is_production else "sandbox",
                        ),
                        platform_fee_bps=_int("JUPITER_PLATFORM_FEE_BPS"),
                        fee_account=env.get("JUPITER_FEE_ACCOUNT"),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.SWAP] = JupiterSwapAdapter(client)
                logger.info("ProviderRegistry: SWAP -> jupiter")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: jupiter init failed: %s", exc)

    @staticmethod
    def _build_offramp(
        *,
        env: Mapping[str, str],
        is_production: bool,
        ports: dict[ProviderCapability, CapabilityPort],
        owned: list[Any],
    ) -> None:
        # Crypto->fiat offramp aggregators. Tried in order; first configured
        # wins. Higher-priority offramps (Circle CPN, Increase bank leg) keep
        # precedence — these fill the slot only when it is still empty.
        if ProviderCapability.OFFRAMP in ports:
            return

        onramper_key = env.get("ONRAMPER_API_KEY")
        if onramper_key:
            try:
                from .offramp import (
                    OnramperOfframpAdapter,
                    OnramperOfframpClient,
                    OnramperOfframpConfig,
                )

                client = OnramperOfframpClient(
                    OnramperOfframpConfig(
                        api_key=onramper_key,
                        environment=env.get(
                            "ONRAMPER_ENVIRONMENT",
                            "production" if is_production else "staging",
                        ),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.OFFRAMP] = OnramperOfframpAdapter(client)
                logger.info("ProviderRegistry: OFFRAMP -> onramper")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: onramper offramp init failed: %s", exc)

        transak_stream_key = env.get("TRANSAK_STREAM_API_KEY") or env.get("TRANSAK_API_KEY")
        if transak_stream_key:
            try:
                from .offramp import (
                    TransakStreamClient,
                    TransakStreamConfig,
                    TransakStreamOfframpAdapter,
                )

                client = TransakStreamClient(
                    TransakStreamConfig(
                        api_key=transak_stream_key,
                        environment=env.get(
                            "TRANSAK_ENVIRONMENT",
                            "production" if is_production else "staging",
                        ),
                        partner_id=env.get("TRANSAK_PARTNER_ID"),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.OFFRAMP] = TransakStreamOfframpAdapter(client)
                logger.info("ProviderRegistry: OFFRAMP -> transak_stream")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: transak stream offramp init failed: %s", exc)

        cb_key_name = env.get("COINBASE_CDP_API_KEY_NAME") or env.get("CDP_API_KEY_NAME")
        cb_key_private = env.get("COINBASE_CDP_API_KEY_PRIVATE") or env.get("CDP_API_KEY_PRIVATE")
        if cb_key_name and cb_key_private:
            try:
                from .offramp import (
                    CoinbaseOfframpAdapter,
                    CoinbaseOfframpClient,
                    CoinbaseOfframpConfig,
                )

                client = CoinbaseOfframpClient(
                    CoinbaseOfframpConfig(
                        api_key_name=cb_key_name,
                        api_key_private=cb_key_private,
                        environment=env.get(
                            "COINBASE_OFFRAMP_ENVIRONMENT",
                            "production" if is_production else "sandbox",
                        ),
                    )
                )
                owned.append(client)
                ports[ProviderCapability.OFFRAMP] = CoinbaseOfframpAdapter(client)
                logger.info("ProviderRegistry: OFFRAMP -> coinbase_offramp")
                return
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: coinbase offramp init failed: %s", exc)

    @staticmethod
    def _build_fiat_accounts(
        *,
        env: Mapping[str, str],
        ports: dict[ProviderCapability, CapabilityPort],
        owned: list[Any],
    ) -> None:
        # Dakota (crypto-native: inbound fiat auto-settles to USDC). Preferred
        # fiat-account provider when configured and Lithic has not taken it.
        dakota_key = env.get("DAKOTA_API_KEY")
        if dakota_key and ProviderCapability.FIAT_ACCOUNT not in ports:
            try:
                from .dakota import DakotaClient, DakotaConfig, DakotaFiatAccountAdapter

                client = DakotaClient(
                    DakotaConfig(
                        api_key=dakota_key,
                        environment=env.get("DAKOTA_ENVIRONMENT", "sandbox"),
                        webhook_public_key_hex=env.get("DAKOTA_WEBHOOK_PUBLIC_KEY"),
                    )
                )
                ports[ProviderCapability.FIAT_ACCOUNT] = DakotaFiatAccountAdapter(client)
                owned.append(client)
                logger.info("ProviderRegistry: FIAT_ACCOUNT -> dakota")
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: dakota init failed: %s", exc)

        # Increase (FDIC partner-bank rails). Fills the fiat-account slot when
        # still empty and provides the offramp bank leg when Circle CPN is
        # absent.  One client backs both adapters.
        increase_key = env.get("INCREASE_API_KEY")
        need_fiat = ProviderCapability.FIAT_ACCOUNT not in ports
        need_offramp = ProviderCapability.OFFRAMP not in ports
        if increase_key and (need_fiat or need_offramp):
            try:
                from .increase import (
                    IncreaseClient,
                    IncreaseConfig,
                    IncreaseFiatAccountAdapter,
                    IncreaseOfframpAdapter,
                )

                client = IncreaseClient(
                    IncreaseConfig(
                        api_key=increase_key,
                        environment=env.get("INCREASE_ENVIRONMENT", "sandbox"),
                        webhook_secret=env.get("INCREASE_WEBHOOK_SECRET"),
                    )
                )
                owned.append(client)
                if need_fiat:
                    ports[ProviderCapability.FIAT_ACCOUNT] = IncreaseFiatAccountAdapter(
                        client
                    )
                    logger.info("ProviderRegistry: FIAT_ACCOUNT -> increase")
                if need_offramp:
                    ports[ProviderCapability.OFFRAMP] = IncreaseOfframpAdapter(client)
                    logger.info("ProviderRegistry: OFFRAMP -> increase")
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: increase init failed: %s", exc)

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

        # Aggregator / widget onramps (env-gated). Each activates only when its
        # keys are set; tried in order, first configured wins. Conduit/Turnkey
        # above keep precedence — these fill the slot only when still empty.
        onramper_key = env.get("ONRAMPER_API_KEY")
        if onramper_key:
            try:
                from .onramp import OnramperClient, OnramperConfig, OnramperOnrampAdapter

                client = OnramperClient(
                    OnramperConfig(
                        api_key=onramper_key,
                        environment=env.get(
                            "ONRAMPER_ENVIRONMENT",
                            "production" if is_production else "staging",
                        ),
                        signing_secret=env.get("ONRAMPER_SIGNING_SECRET"),
                    )
                )
                owned.append(client)
                logger.info("ProviderRegistry: ONRAMP -> onramper")
                return OnramperOnrampAdapter(client)
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: onramper init failed: %s", exc)

        transak_key = env.get("TRANSAK_API_KEY")
        transak_secret = env.get("TRANSAK_API_SECRET")
        if transak_key and transak_secret:
            try:
                from .onramp import TransakClient, TransakConfig, TransakOnrampAdapter

                client = TransakClient(
                    TransakConfig(
                        api_key=transak_key,
                        api_secret=transak_secret,
                        environment=env.get(
                            "TRANSAK_ENVIRONMENT",
                            "production" if is_production else "staging",
                        ),
                        referrer_domain=env.get("TRANSAK_REFERRER_DOMAIN", "app.sardis.sh"),
                    )
                )
                owned.append(client)
                logger.info("ProviderRegistry: ONRAMP -> transak")
                return TransakOnrampAdapter(client)
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: transak init failed: %s", exc)

        daimo_key = env.get("DAIMO_PAY_API_KEY") or env.get("DAIMO_API_KEY")
        if daimo_key:
            try:
                from .onramp import DaimoClient, DaimoConfig, DaimoOnrampAdapter

                client = DaimoClient(
                    DaimoConfig(
                        api_key=daimo_key,
                        environment=env.get(
                            "DAIMO_ENVIRONMENT",
                            "production" if is_production else "sandbox",
                        ),
                    )
                )
                owned.append(client)
                logger.info("ProviderRegistry: ONRAMP -> daimo")
                return DaimoOnrampAdapter(client)
            except Exception as exc:  # noqa: BLE001 - optional path
                logger.warning("ProviderRegistry: daimo init failed: %s", exc)

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

    def swap(self) -> SwapPort:
        return self.get(ProviderCapability.SWAP)  # type: ignore[return-value]

    def bridge(self) -> BridgePort:
        return self.get(ProviderCapability.BRIDGE)  # type: ignore[return-value]

    def card(self) -> CardPort:
        return self.get(ProviderCapability.CARD)  # type: ignore[return-value]

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
