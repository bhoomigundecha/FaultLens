"""
FaultLens Backend — OTLP Ingestion API

Phase 3: Receive telemetry from the OpenTelemetry Collector
  POST /otlp/v1/traces   → accept ExportTraceServiceRequest (protobuf)
  POST /otlp/v1/metrics  → accept ExportMetricsServiceRequest (protobuf)
  POST /otlp/v1/logs     → accept ExportLogsServiceRequest (protobuf)

Phase 4: Trace ingestion + span counting (log span count)
Phase 5: Metrics ingestion — persist MetricPoint rows to PostgreSQL
Phase 6: Log ingestion    — persist LogRecord rows to PostgreSQL
Phase 7: Normalisation — convert proto objects → plain dicts via services.normalise
Phase 8: Persist all telemetry (spans, metrics, logs) to PostgreSQL in bulk

The collector sends application/x-protobuf bodies; JSON is also accepted but
only acknowledged (not yet parsed).
"""
import asyncio
import logging
from typing import Annotated, Awaitable, Callable

from fastapi import APIRouter, Depends, Request, Response, Header, HTTPException
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session as db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/otlp/v1", tags=["ingest"])

# ── helpers ───────────────────────────────────────────────────────────────────

def _is_protobuf(content_type: str | None) -> bool:
    return (content_type or "").startswith("application/x-protobuf")


# ── internal: parse + count helpers (used by tests too) ───────────────────────

def _count_spans(body: bytes) -> int:
    """
    Parse a binary ExportTraceServiceRequest and return the total span count.
    Returns 0 on any parse error.
    """
    try:
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
            ExportTraceServiceRequest,
        )
        req = ExportTraceServiceRequest()
        req.ParseFromString(body)
        return sum(
            len(scope.spans)
            for rs in req.resource_spans
            for scope in rs.scope_spans
        )
    except Exception as exc:
        logger.warning("Span count parse error: %s", exc)
        return 0


def _count_metric_data_points(body: bytes) -> int:
    """
    Parse a binary ExportMetricsServiceRequest and return a data-point count.
    Returns 0 on any parse error.
    """
    try:
        from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
            ExportMetricsServiceRequest,
        )
        req = ExportMetricsServiceRequest()
        req.ParseFromString(body)
        total = 0
        for rm in req.resource_metrics:
            for sm in rm.scope_metrics:
                for m in sm.metrics:
                    for field in ("gauge", "sum", "histogram",
                                  "exponential_histogram", "summary"):
                        data = getattr(m, field, None)
                        if data and hasattr(data, "data_points"):
                            total += len(data.data_points)
                            break
        return total
    except Exception as exc:
        logger.warning("Metric data-point count parse error: %s", exc)
        return 0


def _count_log_records(body: bytes) -> int:
    """
    Parse a binary ExportLogsServiceRequest and return the log record count.
    Returns 0 on any parse error.
    """
    try:
        from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
            ExportLogsServiceRequest,
        )
        req = ExportLogsServiceRequest()
        req.ParseFromString(body)
        return sum(
            len(scope.log_records)
            for rl in req.resource_logs
            for scope in rl.scope_logs
        )
    except Exception as exc:
        logger.warning("Log record count parse error: %s", exc)
        return 0


# ── persistence helpers (Phase 8) ─────────────────────────────────────────────
#
# Each helper runs INSIDE a transaction opened by _ingest(). Telemetry rows are
# written with a Core bulk INSERT (no ORM identity map, no RETURNING) — much
# cheaper than add_all() for hundreds of rows per batch. Service / dependency
# upserts run afterwards in their own SAVEPOINTs (see services.discovery/graph).

async def _persist_spans(db: AsyncSession, body: bytes) -> int:
    """Parse, normalise, bulk-insert spans, upsert services + dependency graph."""
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )
    from app.services.normalise import normalise_traces
    from app.services.discovery import upsert_services_from_spans
    from app.services.graph import upsert_dependencies            # Phase 10
    from app.models.telemetry import Span

    req = ExportTraceServiceRequest()
    req.ParseFromString(body)
    rows = normalise_traces(req.resource_spans)
    if rows:
        await db.execute(insert(Span), rows)
        await upsert_services_from_spans(db, rows)   # Phase 9
        await upsert_dependencies(db, rows)           # Phase 10
    return len(rows)


async def _persist_metrics(db: AsyncSession, body: bytes) -> int:
    """Parse, normalise, bulk-insert metric data points, and touch services."""
    from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
        ExportMetricsServiceRequest,
    )
    from app.services.normalise import normalise_metrics
    from app.services.discovery import upsert_services_from_signals
    from app.models.telemetry import MetricPoint

    req = ExportMetricsServiceRequest()
    req.ParseFromString(body)
    rows = normalise_metrics(req.resource_metrics)
    if rows:
        await db.execute(insert(MetricPoint), rows)
        await upsert_services_from_signals(db, rows)  # Phase 9
    return len(rows)


async def _persist_logs(db: AsyncSession, body: bytes) -> int:
    """Parse, normalise, bulk-insert log records, and touch services."""
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
        ExportLogsServiceRequest,
    )
    from app.services.normalise import normalise_logs
    from app.services.discovery import upsert_services_from_signals
    from app.models.telemetry import LogRecord

    req = ExportLogsServiceRequest()
    req.ParseFromString(body)
    rows = normalise_logs(req.resource_logs)
    if rows:
        await db.execute(insert(LogRecord), rows)
        await upsert_services_from_signals(db, rows)  # Phase 9
    return len(rows)


# ── transaction + retry wrapper ───────────────────────────────────────────────

async def ingest_session() -> AsyncSession | None:
    """
    Test hook. Production yields None → each batch opens its own session and
    transaction. Tests override this dependency with a shared session; the batch
    is then written inside a SAVEPOINT on that session so the test can inspect
    and roll back.
    """
    yield None


_MAX_ATTEMPTS = 3


def _is_retryable(exc: Exception) -> bool:
    """Deadlocks / serialization failures are transient — safe to retry."""
    msg = f"{type(exc).__name__} {exc} {getattr(exc, 'orig', '')}".lower()
    return "deadlock" in msg or "serializ" in msg


async def _ingest(
    signal: str,
    unit: str,
    body: bytes,
    persist: Callable[[AsyncSession, bytes], Awaitable[int]],
    shared: AsyncSession | None = None,
) -> None:
    """
    Persist one OTLP batch in its own transaction.

    - One transaction per batch: either the whole batch lands or none of it.
    - Transient conflicts (deadlocks) are retried with a short backoff.
    - Any other failure is logged on ONE line (no 300-line traceback) and the
      batch is dropped — we still answer 200 so the collector keeps flowing.
    """
    if shared is not None:                      # test path
        async with shared.begin_nested():
            count = await persist(shared, body)
        logger.info("%s persisted | bytes=%d %s=%d", signal, len(body), unit, count)
        return

    if db_session.AsyncSessionLocal is None:
        logger.error("%s dropped — database not initialised", signal)
        return

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            async with db_session.AsyncSessionLocal() as db:
                async with db.begin():
                    count = await persist(db, body)
            logger.info("%s persisted | bytes=%d %s=%d%s", signal, len(body), unit, count,
                        f" (attempt {attempt})" if attempt > 1 else "")
            return
        except Exception as exc:  # noqa: BLE001 — ingest must never crash the request
            if _is_retryable(exc) and attempt < _MAX_ATTEMPTS:
                logger.warning("%s batch hit a lock conflict — retrying (%d/%d)",
                               signal, attempt, _MAX_ATTEMPTS)
                await asyncio.sleep(0.05 * attempt)
                continue
            root = getattr(exc, "orig", None) or exc
            logger.error("%s batch DROPPED | bytes=%d | %s: %s", signal, len(body),
                         type(root).__name__, str(root).splitlines()[0][:300])
            return


async def _handle(request: Request, content_type: str | None, signal: str,
                  unit: str, persist, shared: AsyncSession | None) -> Response:
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty request body")

    if _is_protobuf(content_type):
        await _ingest(signal, unit, body, persist, shared)
    else:
        logger.info("%s received (non-protobuf, skipped) | content_type=%s bytes=%d",
                    signal, content_type, len(body))

    # Always acknowledge — a non-2xx makes the collector retry/back up its queue.
    return Response(content=b"", status_code=200, media_type="application/x-protobuf")


# ── OTLP endpoints ────────────────────────────────────────────────────────────

@router.post("/traces", summary="OTLP trace ingestion")
async def ingest_traces(
    request: Request,
    content_type: Annotated[str | None, Header()] = None,
    shared: AsyncSession | None = Depends(ingest_session),
) -> Response:
    """Receive spans from the OpenTelemetry Collector and persist them."""
    return await _handle(request, content_type, "Traces", "spans", _persist_spans, shared)


@router.post("/metrics", summary="OTLP metrics ingestion")
async def ingest_metrics(
    request: Request,
    content_type: Annotated[str | None, Header()] = None,
    shared: AsyncSession | None = Depends(ingest_session),
) -> Response:
    """Receive metric data points from the OpenTelemetry Collector and persist them."""
    return await _handle(request, content_type, "Metrics", "data_points", _persist_metrics, shared)


@router.post("/logs", summary="OTLP log ingestion")
async def ingest_logs(
    request: Request,
    content_type: Annotated[str | None, Header()] = None,
    shared: AsyncSession | None = Depends(ingest_session),
) -> Response:
    """Receive log records from the OpenTelemetry Collector and persist them."""
    return await _handle(request, content_type, "Logs", "records", _persist_logs, shared)
