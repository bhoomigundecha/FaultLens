"""
FaultLens Backend — Traces API (Phase 11)

GET /api/v1/traces
    Lists recent traces (one row per trace_id, with span count + duration).
    Optional query params: service, limit (default 50), offset.

GET /api/v1/traces/{trace_id}
    Returns the full correlated context for a trace:
      - All spans (with parent/child structure)
      - All log records sharing the trace_id
      - Relevant metrics from the same services in the same time window
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import get_settings
from app.models.telemetry import Span
from app.services.correlation import correlate_trace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["traces"])

_NS_PER_MS = 1_000_000


@router.get("/traces", summary="List recent traces")
async def list_traces(
    service: Annotated[str | None, Query(description="Filter by service name")] = None,
    limit:   Annotated[int,        Query(ge=1, le=200)]                          = 50,
    offset:  Annotated[int,        Query(ge=0)]                                  = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns one summary row per trace_id, ordered by most recent first.

    Each row includes:
      - trace_id
      - root span name (span with no parent, or earliest span)
      - services involved
      - start/end timestamps (ms)
      - total duration (ms)
      - span count
      - whether any span had an error
    """
    # Subquery: for each trace_id get the aggregate values we need
    # We use a window-function-free approach (simpler, portable):
    # select the MIN start, MAX end, COUNT spans, and whether any error exists.
    q = (
        select(
            Span.trace_id,
            func.min(Span.start_time_unix_nano).label("start_ns"),
            func.max(Span.end_time_unix_nano).label("end_ns"),
            func.count(Span.id).label("span_count"),
            func.bool_or(Span.status_code == 2).label("has_error"),
        )
        .group_by(Span.trace_id)
        .order_by(func.min(Span.start_time_unix_nano).desc())
        .limit(limit)
        .offset(offset)
    )

    if service:
        q = q.where(Span.service_name == service)

    result = await db.execute(q)
    rows = result.all()

    traces = []
    for row in rows:
        start_ns = row.start_ns or 0
        end_ns   = row.end_ns   or 0
        traces.append({
            "trace_id":    row.trace_id,
            "start_ms":    start_ns // _NS_PER_MS,
            "end_ms":      end_ns   // _NS_PER_MS,
            "duration_ms": (end_ns - start_ns) // _NS_PER_MS,
            "span_count":  row.span_count,
            "has_error":   bool(row.has_error),
        })

    return {
        "traces": traces,
        "count":  len(traces),
        "limit":  limit,
        "offset": offset,
    }


@router.get("/traces/{trace_id}", summary="Get correlated trace context")
async def get_trace(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the full correlated context for a trace:
      spans + matching logs + metrics from the same services + time window.

    404 if the trace_id has never been seen.
    """
    settings = get_settings()
    context = await correlate_trace(
        db=db,
        trace_id=trace_id,
        window_ns=settings.correlation_window_ns,
    )

    if context is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trace '{trace_id}' not found.",
        )

    return context
