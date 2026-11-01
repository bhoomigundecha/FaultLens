"""
FaultLens Backend — Service Discovery (Phase 9)

Automatically upserts service records from incoming telemetry.
Called by the ingest layer after normalisation, before the session
commits.  Uses PostgreSQL INSERT … ON CONFLICT DO UPDATE so a single
statement handles both first-time registration and counter increments.

Design:
  - One upsert per unique service name per batch (not per span).
  - Counters are incremented atomically using SQL expressions.
  - Never raises — discovery failures are logged and suppressed so
    the telemetry write is not blocked. Each upsert runs in a SAVEPOINT so a
    failure cannot abort the surrounding transaction.
  - Rows are upserted in sorted order (consistent lock order → no deadlocks
    between concurrent ingest requests).
"""
from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# STATUS_CODE == 2 in OTLP proto means ERROR
_ERROR_STATUS = 2


def _aggregate_spans(span_rows: list[dict]) -> dict[str, dict]:
    """
    Aggregate a list of normalised span dicts into per-service counters.

    Returns:
        {service_name: {"min_nano": int, "max_nano": int,
                        "requests": int, "errors": int}}
    """
    agg: dict[str, dict] = {}
    for row in span_rows:
        svc = row.get("service_name")
        if not svc:
            continue
        ts = row.get("start_time_unix_nano", 0) or 0
        is_error = (row.get("status_code") == _ERROR_STATUS)

        if svc not in agg:
            agg[svc] = {"min_nano": ts, "max_nano": ts,
                        "requests": 0, "errors": 0}
        else:
            if ts < agg[svc]["min_nano"]:
                agg[svc]["min_nano"] = ts
            if ts > agg[svc]["max_nano"]:
                agg[svc]["max_nano"] = ts

        agg[svc]["requests"] += 1
        if is_error:
            agg[svc]["errors"] += 1

    return agg


def _service_names_from_rows(rows: list[dict]) -> dict[str, int]:
    """
    Extract {service_name: latest_timestamp_nano} from metric or log rows.
    Used to touch last_seen without affecting request/error counters.
    """
    seen: dict[str, int] = {}
    for row in rows:
        svc = row.get("service_name")
        ts  = row.get("time_unix_nano") or row.get("start_time_unix_nano") or 0
        if svc and ts:
            if svc not in seen or ts > seen[svc]:
                seen[svc] = ts
    return seen


async def upsert_services_from_spans(
    db: AsyncSession,
    span_rows: list[dict],
) -> None:
    """
    Upsert the services table from a batch of normalised span dicts.
    Updates: first_seen, last_seen, request_count, error_count.
    """
    if not span_rows:
        return
    agg = _aggregate_spans(span_rows)
    if not agg:
        return

    try:
        sql = text("""
            INSERT INTO services
                (name, first_seen_unix_nano, last_seen_unix_nano,
                 request_count, error_count)
            VALUES
                (:name, :min_nano, :max_nano, :requests, :errors)
            ON CONFLICT (name) DO UPDATE SET
                first_seen_unix_nano = LEAST(services.first_seen_unix_nano,
                                             EXCLUDED.first_seen_unix_nano),
                last_seen_unix_nano  = GREATEST(services.last_seen_unix_nano,
                                                EXCLUDED.last_seen_unix_nano),
                request_count = services.request_count + EXCLUDED.request_count,
                error_count   = services.error_count   + EXCLUDED.error_count
        """)
        params = [
            {
                "name":     svc,
                "min_nano": data["min_nano"],
                "max_nano": data["max_nano"],
                "requests": data["requests"],
                "errors":   data["errors"],
            }
            for svc, data in agg.items()
        ]
        # Sorted → every request locks service rows in the same order, so
        # concurrent trace/metric/log batches can't deadlock each other.
        params.sort(key=lambda p: p["name"])
        # Savepoint → if this upsert fails, only it is rolled back; the
        # telemetry rows in the same transaction still commit.
        async with db.begin_nested():
            await db.execute(sql, params)
        logger.debug("Upserted %d service(s) from spans", len(params))
    except Exception as exc:
        logger.warning("Service upsert (spans) failed: %s", exc)


async def upsert_services_from_signals(
    db: AsyncSession,
    rows: list[dict],
    ts_field: str = "time_unix_nano",
) -> None:
    """
    Touch last_seen for services seen in metric or log rows.
    Does NOT update request/error counters (those are span-derived).
    If the service doesn't exist yet, insert it with zero counters.
    """
    if not rows:
        return
    seen = _service_names_from_rows(rows)
    if not seen:
        return

    try:
        sql = text("""
            INSERT INTO services
                (name, first_seen_unix_nano, last_seen_unix_nano,
                 request_count, error_count)
            VALUES
                (:name, :ts, :ts, 0, 0)
            ON CONFLICT (name) DO UPDATE SET
                first_seen_unix_nano = LEAST(services.first_seen_unix_nano,
                                             EXCLUDED.first_seen_unix_nano),
                last_seen_unix_nano  = GREATEST(services.last_seen_unix_nano,
                                                EXCLUDED.last_seen_unix_nano)
        """)
        params = sorted(({"name": svc, "ts": ts} for svc, ts in seen.items()),
                        key=lambda p: p["name"])
        async with db.begin_nested():
            await db.execute(sql, params)
        logger.debug("Upserted %d service(s) from signals", len(params))
    except Exception as exc:
        logger.warning("Service upsert (signals) failed: %s", exc)
