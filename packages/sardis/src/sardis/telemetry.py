"""
Sardis SDK Telemetry — auto-registration, heartbeat, and event batching.

Never blocks, never crashes. All operations are best-effort with try/except.
Thread-safe for sync usage, asyncio-safe for async usage.
"""
from __future__ import annotations

import atexit
import logging
import os
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

logger = logging.getLogger("sardis_sdk.telemetry")


@dataclass
class TelemetryConfig:
    """Configuration for SDK telemetry.

    Telemetry is OPT-IN: it is OFF by default and only activates when the
    consumer explicitly opts in (``SARDIS_TELEMETRY_ENABLED=true`` or
    ``TelemetryConfig(enabled=True)``). All fields can be overridden via
    environment variables.
    """

    enabled: bool = False
    agent_id: str | None = None
    agent_name: str = "unnamed-agent"
    framework: str | None = None
    heartbeat_interval: int = 60
    batch_size: int = 10
    batch_interval: int = 10

    @classmethod
    def from_env(cls, **overrides: Any) -> TelemetryConfig:
        """Build config from environment variables, with keyword overrides taking precedence."""
        # Opt-in: default OFF. Only the explicit truthy values turn it on.
        enabled_str = os.environ.get("SARDIS_TELEMETRY_ENABLED", "false")
        enabled = enabled_str.lower() in ("true", "1", "yes", "on")

        agent_id = os.environ.get("SARDIS_AGENT_ID")
        agent_name = os.environ.get("SARDIS_AGENT_NAME", "unnamed-agent")
        heartbeat_interval = int(os.environ.get("SARDIS_HEARTBEAT_INTERVAL", "60"))
        batch_size = int(os.environ.get("SARDIS_BATCH_SIZE", "10"))
        batch_interval = int(os.environ.get("SARDIS_BATCH_INTERVAL", "10"))

        cfg = cls(
            enabled=enabled,
            agent_id=agent_id,
            agent_name=agent_name,
            heartbeat_interval=heartbeat_interval,
            batch_size=batch_size,
            batch_interval=batch_interval,
        )
        for k, v in overrides.items():
            if v is not None and hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg


@dataclass
class TelemetryEvent:
    """A single telemetry event queued for batching."""

    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class SardisTelemetry:
    """SDK telemetry: auto-registration, heartbeat, and event batching.

    Designed to be completely non-blocking and crash-proof.
    All public methods swallow exceptions and log at debug level.
    """

    MAX_QUEUE_SIZE = 1000

    def __init__(
        self,
        config: TelemetryConfig,
        base_url: str,
        api_key: str,
        sdk_version: str,
    ) -> None:
        self._config = config
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._sdk_version = sdk_version

        self._session_id = str(uuid.uuid4())
        self._agent_id: str | None = config.agent_id
        self._registered = False

        # Event queue (thread-safe via lock)
        self._queue: deque[TelemetryEvent] = deque(maxlen=self.MAX_QUEUE_SIZE)
        self._lock = threading.Lock()

        # Background threads
        self._heartbeat_timer: threading.Timer | None = None
        self._flush_timer: threading.Timer | None = None
        self._shutdown_flag = threading.Event()

        # Lazy httpx client for telemetry calls
        self._http: httpx.Client | None = None

    # ------------------------------------------------------------------
    # Internal HTTP
    # ------------------------------------------------------------------

    def _get_http(self) -> httpx.Client:
        if self._http is None or self._http.is_closed:
            import httpx

            self._http = httpx.Client(
                base_url=self._base_url,
                timeout=httpx.Timeout(5.0),
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http

    def _post(self, path: str, json_body: dict[str, Any]) -> dict[str, Any] | None:
        """Fire a POST request. Returns response JSON or None on failure."""
        try:
            resp = self._get_http().post(path, json=json_body)
            if resp.status_code < 400:
                return resp.json()
            logger.debug("Telemetry POST %s returned %d", path, resp.status_code)
        except Exception:
            logger.debug("Telemetry POST %s failed", path, exc_info=True)
        return None

    # ------------------------------------------------------------------
    # Layer 2: Registration + Heartbeat
    # ------------------------------------------------------------------

    def ensure_registered(self) -> None:
        """Register agent with the server (idempotent). Never raises."""
        if not self._config.enabled or self._registered:
            return
        try:
            payload: dict[str, Any] = {
                "name": self._config.agent_name,
                "session_id": self._session_id,
                "sdk_version": self._sdk_version,
            }
            if self._agent_id:
                payload["agent_id"] = self._agent_id
            if self._config.framework:
                payload["framework"] = self._config.framework

            result = self._post("/api/v2/agents/auto-register", payload)
            if result:
                self._agent_id = result.get("agent_id", self._agent_id)
                self._registered = True
                logger.debug(
                    "Agent registered: id=%s, created=%s",
                    self._agent_id,
                    result.get("created", False),
                )
        except Exception:
            logger.debug("ensure_registered failed", exc_info=True)

    def start_heartbeat(self) -> None:
        """Start the background heartbeat thread. Never raises."""
        if not self._config.enabled:
            return
        try:
            self._schedule_heartbeat()
            atexit.register(self.shutdown)
        except Exception:
            logger.debug("start_heartbeat failed", exc_info=True)

    def _schedule_heartbeat(self) -> None:
        if self._shutdown_flag.is_set():
            return
        # Jitter: interval * (0.8 + 0.4 * random()) to avoid thundering herd
        jittered = self._config.heartbeat_interval * (0.8 + 0.4 * random.random())
        self._heartbeat_timer = threading.Timer(jittered, self._heartbeat_tick)
        self._heartbeat_timer.daemon = True
        self._heartbeat_timer.start()

    def _heartbeat_tick(self) -> None:
        if self._shutdown_flag.is_set():
            return
        try:
            payload: dict[str, Any] = {"session_id": self._session_id}
            if self._agent_id:
                payload["agent_id"] = self._agent_id
            self._post("/api/v2/agents/heartbeat", payload)
        except Exception:
            logger.debug("heartbeat tick failed", exc_info=True)
        self._schedule_heartbeat()

    # ------------------------------------------------------------------
    # Layer 3: Event Batching
    # ------------------------------------------------------------------

    def track(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Queue a telemetry event. Never blocks, never raises."""
        if not self._config.enabled:
            return
        try:
            event = TelemetryEvent(event_type=event_type, data=data or {})
            with self._lock:
                self._queue.append(event)
                queue_len = len(self._queue)

            # Auto-flush if batch size reached
            if queue_len >= self._config.batch_size:
                self._do_flush()
        except Exception:
            logger.debug("track failed", exc_info=True)

    def start_flush_timer(self) -> None:
        """Start periodic flush timer. Never raises."""
        if not self._config.enabled:
            return
        try:
            self._schedule_flush()
        except Exception:
            logger.debug("start_flush_timer failed", exc_info=True)

    def _schedule_flush(self) -> None:
        if self._shutdown_flag.is_set():
            return
        self._flush_timer = threading.Timer(
            float(self._config.batch_interval), self._flush_tick
        )
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _flush_tick(self) -> None:
        if self._shutdown_flag.is_set():
            return
        self._do_flush()
        self._schedule_flush()

    def flush(self) -> None:
        """Flush queued events immediately. Never raises."""
        try:
            self._do_flush()
        except Exception:
            logger.debug("flush failed", exc_info=True)

    def _do_flush(self) -> None:
        """Drain the queue and POST events batch to the server."""
        if not self._agent_id:
            return

        with self._lock:
            if not self._queue:
                return
            batch = list(self._queue)
            self._queue.clear()

        events_payload = [
            {
                "event_type": e.event_type,
                "data": e.data,
                "sdk_timestamp": e.timestamp,
            }
            for e in batch
        ]

        self._post(
            f"/api/v2/agents/{self._agent_id}/events/batch",
            {"events": events_payload, "session_id": self._session_id},
        )

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    def get_headers(self) -> dict[str, str]:
        """Return telemetry headers to merge into API requests."""
        headers: dict[str, str] = {}
        if self._agent_id:
            headers["X-Sardis-Agent-Id"] = self._agent_id
        headers["X-Sardis-Session-Id"] = self._session_id
        return headers

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Stop heartbeat, flush remaining events, close HTTP client. Never raises."""
        try:
            self._shutdown_flag.set()

            if self._heartbeat_timer:
                self._heartbeat_timer.cancel()
                self._heartbeat_timer = None

            if self._flush_timer:
                self._flush_timer.cancel()
                self._flush_timer = None

            self._do_flush()

            if self._http and not self._http.is_closed:
                self._http.close()
                self._http = None
        except Exception:
            logger.debug("shutdown failed", exc_info=True)


# ---------------------------------------------------------------------------
# Async variant
# ---------------------------------------------------------------------------


class AsyncSardisTelemetry:
    """Async telemetry using asyncio tasks instead of threads.

    Same API surface as SardisTelemetry but uses async HTTP and asyncio timers.
    """

    MAX_QUEUE_SIZE = 1000

    def __init__(
        self,
        config: TelemetryConfig,
        base_url: str,
        api_key: str,
        sdk_version: str,
    ) -> None:
        self._config = config
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._sdk_version = sdk_version

        self._session_id = str(uuid.uuid4())
        self._agent_id: str | None = config.agent_id
        self._registered = False

        self._queue: deque[TelemetryEvent] = deque(maxlen=self.MAX_QUEUE_SIZE)
        self._shutdown_flag = False

        self._heartbeat_task: Any = None
        self._flush_task: Any = None
        self._http: httpx.AsyncClient | None = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            import httpx

            self._http = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(5.0),
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http

    async def _post(self, path: str, json_body: dict[str, Any]) -> dict[str, Any] | None:
        try:
            client = await self._get_http()
            resp = await client.post(path, json=json_body)
            if resp.status_code < 400:
                return resp.json()
            logger.debug("Async telemetry POST %s returned %d", path, resp.status_code)
        except Exception:
            logger.debug("Async telemetry POST %s failed", path, exc_info=True)
        return None

    async def ensure_registered(self) -> None:
        if not self._config.enabled or self._registered:
            return
        try:
            payload: dict[str, Any] = {
                "name": self._config.agent_name,
                "session_id": self._session_id,
                "sdk_version": self._sdk_version,
            }
            if self._agent_id:
                payload["agent_id"] = self._agent_id
            if self._config.framework:
                payload["framework"] = self._config.framework

            result = await self._post("/api/v2/agents/auto-register", payload)
            if result:
                self._agent_id = result.get("agent_id", self._agent_id)
                self._registered = True
                logger.debug(
                    "Agent registered (async): id=%s, created=%s",
                    self._agent_id,
                    result.get("created", False),
                )
        except Exception:
            logger.debug("ensure_registered (async) failed", exc_info=True)

    async def start_heartbeat(self) -> None:
        if not self._config.enabled:
            return
        try:
            import asyncio

            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        except Exception:
            logger.debug("start_heartbeat (async) failed", exc_info=True)

    async def _heartbeat_loop(self) -> None:
        import asyncio

        while not self._shutdown_flag:
            jittered = self._config.heartbeat_interval * (0.8 + 0.4 * random.random())
            await asyncio.sleep(jittered)
            if self._shutdown_flag:
                break
            try:
                payload: dict[str, Any] = {"session_id": self._session_id}
                if self._agent_id:
                    payload["agent_id"] = self._agent_id
                await self._post("/api/v2/agents/heartbeat", payload)
            except Exception:
                logger.debug("heartbeat tick (async) failed", exc_info=True)

    def track(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Queue event (sync-safe, can be called from any context)."""
        if not self._config.enabled:
            return
        try:
            event = TelemetryEvent(event_type=event_type, data=data or {})
            self._queue.append(event)
        except Exception:
            logger.debug("track (async) failed", exc_info=True)

    async def start_flush_timer(self) -> None:
        if not self._config.enabled:
            return
        try:
            import asyncio

            self._flush_task = asyncio.create_task(self._flush_loop())
        except Exception:
            logger.debug("start_flush_timer (async) failed", exc_info=True)

    async def _flush_loop(self) -> None:
        import asyncio

        while not self._shutdown_flag:
            await asyncio.sleep(float(self._config.batch_interval))
            if self._shutdown_flag:
                break
            await self._do_flush()

    async def flush(self) -> None:
        try:
            await self._do_flush()
        except Exception:
            logger.debug("flush (async) failed", exc_info=True)

    async def _do_flush(self) -> None:
        if not self._agent_id or not self._queue:
            return

        batch = list(self._queue)
        self._queue.clear()

        events_payload = [
            {
                "event_type": e.event_type,
                "data": e.data,
                "sdk_timestamp": e.timestamp,
            }
            for e in batch
        ]

        await self._post(
            f"/api/v2/agents/{self._agent_id}/events/batch",
            {"events": events_payload, "session_id": self._session_id},
        )

    def get_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._agent_id:
            headers["X-Sardis-Agent-Id"] = self._agent_id
        headers["X-Sardis-Session-Id"] = self._session_id
        return headers

    async def shutdown(self) -> None:
        try:
            self._shutdown_flag = True

            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                self._heartbeat_task = None

            if self._flush_task and not self._flush_task.done():
                self._flush_task.cancel()
                self._flush_task = None

            await self._do_flush()

            if self._http and not self._http.is_closed:
                await self._http.aclose()
                self._http = None
        except Exception:
            logger.debug("shutdown (async) failed", exc_info=True)
