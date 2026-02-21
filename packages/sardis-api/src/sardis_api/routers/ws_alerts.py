"""WebSocket endpoint for real-time spending alerts."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time alerts."""

    def __init__(self) -> None:
        # Map: organization_id -> set of websocket connections
        self.active_connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, organization_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        async with self._lock:
            if organization_id not in self.active_connections:
                self.active_connections[organization_id] = set()
            self.active_connections[organization_id].add(websocket)

        logger.info(
            f"WebSocket connected for org={organization_id}, "
            f"total={len(self.active_connections[organization_id])}"
        )

    async def disconnect(self, websocket: WebSocket, organization_id: str) -> None:
        """Unregister a WebSocket connection."""
        async with self._lock:
            if organization_id in self.active_connections:
                self.active_connections[organization_id].discard(websocket)
                if not self.active_connections[organization_id]:
                    del self.active_connections[organization_id]

        logger.info(
            f"WebSocket disconnected for org={organization_id}, "
            f"remaining={len(self.active_connections.get(organization_id, []))}"
        )

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket) -> None:
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, organization_id: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all connections in an organization."""
        async with self._lock:
            connections = self.active_connections.get(organization_id, set()).copy()

        if not connections:
            logger.debug(f"No active connections for org={organization_id}")
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Send to all connections, removing dead ones
        dead_connections = set()
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                dead_connections.add(connection)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                if organization_id in self.active_connections:
                    self.active_connections[organization_id] -= dead_connections

    async def broadcast_all(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        async with self._lock:
            all_orgs = list(self.active_connections.keys())

        for org_id in all_orgs:
            await self.broadcast(org_id, message)

    def get_connection_count(self, organization_id: Optional[str] = None) -> int:
        """Get number of active connections."""
        if organization_id:
            return len(self.active_connections.get(organization_id, set()))
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
connection_manager = ConnectionManager()


def _validate_token(token: str) -> tuple[bool, str]:
    """
    Validate authentication token and extract organization_id.

    In production, this should verify JWT or API key.
    For now, we'll accept tokens in format: "org_{org_id}" or validate against API keys.

    Returns:
        (is_valid, organization_id)
    """
    if not token:
        return False, ""

    # Simple token format: org_<organization_id>
    # In production, decode JWT or validate API key
    if token.startswith("org_"):
        org_id = token[4:]
        if org_id:
            return True, org_id

    # For demo/dev: accept any token as org ID
    return True, token


@router.websocket("/ws/alerts")
async def websocket_alerts(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
) -> None:
    """
    WebSocket endpoint for real-time alerts.

    Connect with authentication token:
    ws://localhost:8000/api/v2/ws/alerts?token=<your_token>

    Messages sent to client:
    - Alert notifications (type: "alert")
    - Heartbeat pings (type: "ping")
    - System messages (type: "system")

    Client should respond to ping messages with pong to keep connection alive.
    """
    # Validate token
    is_valid, organization_id = _validate_token(token)
    if not is_valid:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    # Connect client
    await connection_manager.connect(websocket, organization_id)

    # Send welcome message
    await connection_manager.send_personal_message(
        {
            "type": "system",
            "message": "Connected to Sardis alert stream",
            "organization_id": organization_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        websocket,
    )

    # Heartbeat task
    heartbeat_interval = 30  # seconds
    last_heartbeat = asyncio.get_event_loop().time()

    try:
        while True:
            # Check if we should send heartbeat
            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat >= heartbeat_interval:
                try:
                    await websocket.send_json({"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()})
                    last_heartbeat = current_time
                except Exception:
                    # Connection dead
                    break

            # Wait for messages from client (with timeout for heartbeat)
            try:
                # Use wait_for to timeout and send heartbeat
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=heartbeat_interval,
                )

                # Handle client messages
                try:
                    message = json.loads(data)
                    message_type = message.get("type", "")

                    if message_type == "pong":
                        # Client responded to ping
                        logger.debug(f"Received pong from org={organization_id}")
                    elif message_type == "subscribe":
                        # Client wants to subscribe to specific alert types
                        # TODO: Implement filtering
                        await connection_manager.send_personal_message(
                            {
                                "type": "system",
                                "message": "Subscription preferences updated",
                            },
                            websocket,
                        )
                    else:
                        logger.debug(f"Received unknown message type: {message_type}")

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from org={organization_id}")

            except asyncio.TimeoutError:
                # Timeout waiting for message, continue to send heartbeat
                continue

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally for org={organization_id}")
    except Exception as e:
        logger.error(f"WebSocket error for org={organization_id}: {e}")
    finally:
        await connection_manager.disconnect(websocket, organization_id)


@router.get("/ws/alerts/status")
async def websocket_status() -> JSONResponse:
    """Get WebSocket connection status."""
    return JSONResponse(
        content={
            "total_connections": connection_manager.get_connection_count(),
            "organizations": len(connection_manager.active_connections),
        }
    )


# Export connection manager for use in alert channels
def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager
