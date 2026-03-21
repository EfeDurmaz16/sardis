"""Server-Sent Events stream for real-time dashboard updates."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory event bus — maps org_id to list of subscriber queues
_subscribers: dict[str, list[asyncio.Queue]] = {}


async def publish_event(org_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Publish an event to all SSE subscribers for an org.

    Call this from payment/MPP/policy endpoints to push real-time updates.

    Usage:
        from sardis_api.routers.event_stream import publish_event
        await publish_event(org_id, "payment.completed", {"amount": "10.00", ...})
    """
    event = {
        "type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": data,
    }
    queues = _subscribers.get(org_id, [])
    for queue in queues:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("SSE queue full for org %s, dropping event", org_id)


@router.get("/stream")
async def event_stream(
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Server-Sent Events stream of real-time events.

    Events include:
    - payment.completed — a payment was executed
    - payment.blocked — a payment was blocked by policy
    - session.created — MPP session opened
    - session.closed — MPP session closed
    - mandate.created — spending mandate created
    - agent.created — new agent registered
    - faucet.drip — test USDC dispensed

    Connection stays open. Sends keepalive comments every 30s.
    """
    org_id = principal.org_id
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    # Register subscriber
    if org_id not in _subscribers:
        _subscribers[org_id] = []
    _subscribers[org_id].append(queue)

    async def generate():
        try:
            # Send initial connection event
            connected = {
                "type": "connected",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {"org_id": org_id, "environment": getattr(principal, "environment", "test")},
            }
            yield f"data: {json.dumps(connected)}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"event: {event.get('type', 'message')}\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive comment
                    yield f": keepalive {datetime.now(UTC).isoformat()}\n\n"
        finally:
            # Unregister subscriber
            try:
                _subscribers.get(org_id, []).remove(queue)
                if org_id in _subscribers and not _subscribers[org_id]:
                    del _subscribers[org_id]
            except (ValueError, KeyError):
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/recent")
async def get_recent_events(
    limit: int = 50,
    principal: Principal = Depends(require_principal),
):
    """Get recent events (polling fallback for SSE).

    Returns the last N events. Use this if SSE is not supported.
    """
    # For now, return empty — events are real-time only via SSE
    # In production, this would query from Redis or DB
    return {
        "events": [],
        "count": 0,
        "message": "Use GET /api/v2/events/stream for real-time SSE updates",
    }
