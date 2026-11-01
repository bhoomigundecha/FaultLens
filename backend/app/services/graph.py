"""
FaultLens Backend — Dependency Graph Builder (Phase 10)

Derives directed service→service call edges from span parent/child
relationships within an incoming batch, then upserts them atomically.

Algorithm
─────────
Within a single batch of normalised span rows:

  1. Build a lookup table:  span_id → (service_name, start_time_ns, status_code)
     from all spans in the batch.

  2. For each span that has a parent_span_id:
       • Look up the parent span in the lookup table.
       • If the parent's service differs from the child's service:
           → record edge  parent_service → child_service

  3. Aggregate edges into per-pair counters (request_count, error_count,
     min_nano, max_nano) — one pass, no repeated dict lookups.

  4. Bulk-upsert into service_dependencies via
     INSERT … ON CONFLICT (source_service, target_service) DO UPDATE.

Limitations / trade-offs
─────────────────────────
• Only intra-batch cross-service links are detected.  If the parent span
  arrived in a previous batch, it will not be in the lookup table and the
  edge is missed for that call — but will be picked up when a later batch
  contains both parent and child.  Over time the graph converges to the
  true topology.

• We intentionally do NOT do a DB round-trip to look up missing parents.
  That would turn every ingest request into a DB read, creating a blocking
  dependency and defeating the unbounded-memory-usage goal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_ERROR_STATUS = 2   # OTLP StatusCode.ERROR


# ── Internal structures ───────────────────────────────────────────────────────

class _SpanInfo(NamedTuple):
    service: str
    start_ns: int
    is_error: bool


@dataclass
class _Edge:
    source:   str
    target:   str
    min_ns:   int
    max_ns:   int
    requests: int = 0
    errors:   int = 0


# ── Core extraction ───────────────────────────────────────────────────────────

def extract_dependencies(span_rows: list[dict]) -> list[_Edge]:
    """
    Pure-Python analysis of a normalised span batch.
    Returns one _Edge per unique (source, target) pair found in the batch.
    """
    if not span_rows:
        return []

    # Step 1: build span_id → info lookup (only for spans that have a service)
    lookup: dict[str, _SpanInfo] = {}
    for row in span_rows:
        sid = row.get("span_id")
        svc = row.get("service_name")
        if sid and svc:
            lookup[sid] = _SpanInfo(
                service  = svc,
                start_ns = row.get("start_time_unix_nano") or 0,
                is_error = (row.get("status_code") == _ERROR_STATUS),
            )

    # Step 2 + 3: find cross-service edges and aggregate counters
    edges: dict[tuple[str, str], _Edge] = {}

    for row in span_rows:
        child_svc = row.get("service_name")
        parent_id = row.get("parent_span_id")
        if not child_svc or not parent_id:
            continue

        parent_info = lookup.get(parent_id)
        if parent_info is None or parent_info.service == child_svc:
            continue  # same-service call or unknown parent — skip

        key = (parent_info.service, child_svc)
        ts  = row.get("start_time_unix_nano") or 0
        is_error = (row.get("status_code") == _ERROR_STATUS)

        if key not in edges:
            edges[key] = _Edge(
                source   = parent_info.service,
                target   = child_svc,
                min_ns   = ts,
                max_ns   = ts,
                requests = 0,
                errors   = 0,
            )
        e = edges[key]
        if ts < e.min_ns:
            e.min_ns = ts
        if ts > e.max_ns:
            e.max_ns = ts
        e.requests += 1
        if is_error:
            e.errors += 1

    return list(edges.values())


# ── DB upsert ─────────────────────────────────────────────────────────────────

async def upsert_dependencies(
    db: AsyncSession,
    span_rows: list[dict],
) -> None:
    """
    Extract cross-service dependency edges from a span batch and upsert them.
    Called by _persist_spans() after the spans have been added to the session.
    Never raises — failures are logged and suppressed.
    """
    edges = extract_dependencies(span_rows)
    if not edges:
        return

    try:
        sql = text("""
            INSERT INTO service_dependencies
                (source_service, target_service,
                 first_seen_unix_nano, last_seen_unix_nano,
                 request_count, error_count)
            VALUES
                (:source, :target, :min_ns, :max_ns, :requests, :errors)
            ON CONFLICT (source_service, target_service) DO UPDATE SET
                first_seen_unix_nano = LEAST(
                    service_dependencies.first_seen_unix_nano,
                    EXCLUDED.first_seen_unix_nano),
                last_seen_unix_nano  = GREATEST(
                    service_dependencies.last_seen_unix_nano,
                    EXCLUDED.last_seen_unix_nano),
                request_count = service_dependencies.request_count
                              + EXCLUDED.request_count,
                error_count   = service_dependencies.error_count
                              + EXCLUDED.error_count
        """)
        params = [
            {
                "source":   e.source,
                "target":   e.target,
                "min_ns":   e.min_ns,
                "max_ns":   e.max_ns,
                "requests": e.requests,
                "errors":   e.errors,
            }
            for e in edges
        ]
        params.sort(key=lambda p: (p["source"], p["target"]))  # consistent lock order
        async with db.begin_nested():                           # failure stays local
            await db.execute(sql, params)
        logger.debug(
            "Upserted %d dependency edge(s): %s",
            len(edges),
            [(e.source, e.target) for e in edges],
        )
    except Exception as exc:
        logger.warning("Dependency upsert failed: %s", exc)
