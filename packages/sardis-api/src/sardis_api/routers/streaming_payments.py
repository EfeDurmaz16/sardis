"""Streaming Payment API — SSE-based pay-per-use payments.

Opens an SSE connection that streams payment events as work
units are consumed (e.g., LLM tokens, API calls, compute seconds).
Backed by TempoStreamChannel for efficient settlement.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)

# In-memory stream sessions (production: Redis or DB)
_active_streams: dict[str, dict] = {}


class OpenStreamRequest(BaseModel):
    service_address: str = Field(..., description="Service provider address")
    deposit_amount: Decimal = Field(..., gt=0, description="Initial deposit")
    token: str = Field(default="USDC")
    unit_price: Decimal = Field(..., gt=0, description="Price per work unit")
    max_units: int | None = Field(default=None, ge=1, description="Max units (None=unlimited up to deposit)")
    duration_hours: int = Field(default=24, ge=1, le=168)


class StreamResponse(BaseModel):
    stream_id: str
    channel_id: str
    deposit_amount: str
    unit_price: str
    units_consumed: int
    amount_consumed: str
    remaining: str
    status: str
    sse_url: str


class ConsumeUnitRequest(BaseModel):
    stream_id: str
    units: int = Field(default=1, ge=1, le=1000)
    metadata: dict | None = None


class ConsumeResponse(BaseModel):
    stream_id: str
    units_consumed: int
    total_units: int
    amount_this_batch: str
    total_amount: str
    remaining: str
    voucher_sequence: int


@router.post(
    "/payments/stream/open",
    response_model=StreamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open a streaming payment channel",
)
async def open_stream(
    req: OpenStreamRequest,
    principal: Principal = Depends(require_principal),
) -> StreamResponse:
    """Open an SSE streaming payment channel backed by TempoStreamChannel."""
    from sardis_chain.tempo.stream_channel import TempoStreamChannel
    from uuid import uuid4

    channel_mgr = TempoStreamChannel()
    session = await channel_mgr.open(
        client=principal.principal_id,
        service=req.service_address,
        deposit=req.deposit_amount,
        token=req.token,
        duration_hours=req.duration_hours,
    )

    stream_id = f"stream_{uuid4().hex[:12]}"
    _active_streams[stream_id] = {
        "channel_id": session.channel_id,
        "channel_mgr": channel_mgr,
        "unit_price": req.unit_price,
        "max_units": req.max_units,
        "units_consumed": 0,
        "amount_consumed": Decimal("0"),
        "deposit": req.deposit_amount,
        "status": "open",
        "events": asyncio.Queue(),
    }

    return StreamResponse(
        stream_id=stream_id,
        channel_id=session.channel_id,
        deposit_amount=str(req.deposit_amount),
        unit_price=str(req.unit_price),
        units_consumed=0,
        amount_consumed="0",
        remaining=str(req.deposit_amount),
        status="open",
        sse_url=f"/api/v2/payments/stream/{stream_id}/events",
    )


@router.post(
    "/payments/stream/{stream_id}/consume",
    response_model=ConsumeResponse,
    summary="Consume work units and issue payment voucher",
)
async def consume_units(
    stream_id: str,
    req: ConsumeUnitRequest,
    principal: Principal = Depends(require_principal),
) -> ConsumeResponse:
    """Record consumption and issue off-chain payment voucher."""
    stream = _active_streams.get(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if stream["status"] != "open":
        raise HTTPException(status_code=409, detail=f"Stream is {stream['status']}")

    amount = stream["unit_price"] * req.units
    new_total = stream["amount_consumed"] + amount

    if new_total > stream["deposit"]:
        raise HTTPException(
            status_code=422,
            detail=f"Would exceed deposit: {new_total} > {stream['deposit']}",
        )
    if stream["max_units"] and stream["units_consumed"] + req.units > stream["max_units"]:
        raise HTTPException(
            status_code=422,
            detail=f"Would exceed max units: {stream['units_consumed'] + req.units} > {stream['max_units']}",
        )

    # Issue voucher via stream channel
    channel_mgr = stream["channel_mgr"]
    voucher = channel_mgr.issue_voucher(stream["channel_id"], amount)

    stream["units_consumed"] += req.units
    stream["amount_consumed"] = new_total

    # Push SSE event
    event = {
        "type": "payment",
        "units": req.units,
        "amount": str(amount),
        "total_units": stream["units_consumed"],
        "total_amount": str(new_total),
        "voucher_sequence": voucher.sequence,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    await stream["events"].put(event)

    remaining = stream["deposit"] - new_total
    return ConsumeResponse(
        stream_id=stream_id,
        units_consumed=req.units,
        total_units=stream["units_consumed"],
        amount_this_batch=str(amount),
        total_amount=str(new_total),
        remaining=str(remaining),
        voucher_sequence=voucher.sequence,
    )


@router.get(
    "/payments/stream/{stream_id}/events",
    summary="SSE event stream for payment updates",
)
async def stream_events(
    stream_id: str,
    principal: Principal = Depends(require_principal),
):
    """Server-Sent Events stream for real-time payment updates."""
    stream = _active_streams.get(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    async def event_generator():
        queue: asyncio.Queue = stream["events"]
        yield f"data: {json.dumps({'type': 'connected', 'stream_id': stream_id})}\n\n"
        while stream["status"] == "open":
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield f": keepalive {datetime.now(UTC).isoformat()}\n\n"

        yield f"data: {json.dumps({'type': 'closed', 'stream_id': stream_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/payments/stream/{stream_id}/settle",
    response_model=StreamResponse,
    summary="Settle and close a streaming payment channel",
)
async def settle_stream(
    stream_id: str,
    principal: Principal = Depends(require_principal),
) -> StreamResponse:
    """Settle all accumulated vouchers on-chain and close the stream."""
    stream = _active_streams.get(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    channel_mgr = stream["channel_mgr"]
    session = await channel_mgr.settle(stream["channel_id"])
    stream["status"] = "settled"

    return StreamResponse(
        stream_id=stream_id,
        channel_id=stream["channel_id"],
        deposit_amount=str(stream["deposit"]),
        unit_price=str(stream["unit_price"]),
        units_consumed=stream["units_consumed"],
        amount_consumed=str(stream["amount_consumed"]),
        remaining=str(stream["deposit"] - stream["amount_consumed"]),
        status="settled",
        sse_url=f"/api/v2/payments/stream/{stream_id}/events",
    )
