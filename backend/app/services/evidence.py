"""
FaultLens Backend — Evidence Assembler (Phase 15)

Aggregates all pipeline outputs for one incident into a single structured
context dict that is ready to inject into the Groq prompt (Phase 17).

This is a read-only aggregator — it writes nothing to the DB.

What it gathers (matching the research-aligned prompt structure from GALA/RCAgent):
  1. Incident record         — title, severity, affected_services, rule
  2. RCA result              — root_cause_service, confidence, propagation_path
  3. Active anomalies        — for the affected services only (compressed)
  4. Service graph subgraph  — nodes and edges involving the affected services
  5. Evidence                — top error spans and error log snippets

Why compress?
─────────────
The LLM has a finite context window (~32k tokens for llama-3.3-70b-versatile).
Passing raw span tables would overflow it. Instead we pass:
  - Top 5 error spans per affected service (by occurrence count)
  - Top 5 error log messages per affected service (by occurrence count)
  - Only the graph subgraph reachable from the affected services (not the full graph)

This is the "evidence compression" pattern from GALA/GALA+ (ASE 2024).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.rca import RootCauseAnalysis
from app.models.anomaly import Anomaly
from app.models.dependency import ServiceDependency
from app.models.telemetry import Span, LogRecord

logger = logging.getLogger(__name__)

# Max items to include per category (keeps context window lean)
_MAX_ERROR_SPANS  = 5
_MAX_ERROR_LOGS   = 5
_MAX_ANOMALIES    = 10

_NS_PER_MS = 1_000_000


# ── Individual loaders ─────────────────────────────────────────────────────────

async def _load_incident(db: AsyncSession, incident_id: int) -> Incident | None:
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    return result.scalar_one_or_none()


async def _load_rca(db: AsyncSession, incident_id: int) -> RootCauseAnalysis | None:
    result = await db.execute(
        select(RootCauseAnalysis).where(
            RootCauseAnalysis.incident_id == incident_id
        )
    )
    return result.scalar_one_or_none()


async def _load_anomalies(
    db: AsyncSession,
    services: list[str],
) -> list[Anomaly]:
    """Active anomalies for the given services, sorted by |z_score| desc."""
    result = await db.execute(
        select(Anomaly)
        .where(
            Anomaly.is_active == True,  # noqa: E712
            Anomaly.service_name.in_(services),
        )
        .order_by(Anomaly.z_score.desc())
        .limit(_MAX_ANOMALIES)
    )
    return result.scalars().all()


async def _load_graph_subgraph(
    db: AsyncSession,
    services: list[str],
) -> list[ServiceDependency]:
    """
    Dependency edges where source OR target is in the affected services.
    This gives the 1-hop neighbourhood — enough for the LLM to reason about.
    """
    result = await db.execute(
        select(ServiceDependency).where(
            ServiceDependency.source_service.in_(services) |
            ServiceDependency.target_service.in_(services)
        )
    )
    return result.scalars().all()


async def _load_error_spans(
    db: AsyncSession,
    services: list[str],
) -> list[dict[str, Any]]:
    """
    Top N error span names per service, by occurrence count.
    Returns compact dicts — not full ORM rows.
    """
    result = await db.execute(
        select(
            Span.service_name,
            Span.name,
            Span.status_message,
            func.count(Span.id).label("count"),
        )
        .where(
            Span.service_name.in_(services),
            Span.status_code == 2,   # ERROR status
        )
        .group_by(Span.service_name, Span.name, Span.status_message)
        .order_by(func.count(Span.id).desc())
        .limit(_MAX_ERROR_SPANS)
    )
    return [
        {
            "service_name":   row.service_name,
            "span_name":      row.name,
            "error_message":  row.status_message or "",
            "occurrence_count": row.count,
        }
        for row in result.all()
    ]


async def _load_error_logs(
    db: AsyncSession,
    services: list[str],
) -> list[dict[str, Any]]:
    """
    Top N unique error log messages per service, by occurrence count.
    Only returns severity ≥ ERROR (severity_number >= 17).
    """
    result = await db.execute(
        select(
            LogRecord.service_name,
            LogRecord.body,
            LogRecord.severity_text,
            func.count(LogRecord.id).label("count"),
        )
        .where(
            LogRecord.service_name.in_(services),
            LogRecord.severity_number >= 17,   # ERROR and above
        )
        .group_by(LogRecord.service_name, LogRecord.body, LogRecord.severity_text)
        .order_by(func.count(LogRecord.id).desc())
        .limit(_MAX_ERROR_LOGS)
    )
    return [
        {
            "service_name":     row.service_name,
            "message":          row.body or "",
            "severity":         row.severity_text or "ERROR",
            "occurrence_count": row.count,
        }
        for row in result.all()
    ]


# ── Evidence builder ───────────────────────────────────────────────────────────

def _build_graph_dict(
    deps: list[ServiceDependency],
    services: list[str],
) -> dict[str, Any]:
    """Convert dependency rows into the graph dict expected by the prompt."""
    node_set: set[str] = set(services)
    edges = []
    for d in deps:
        node_set.add(d.source_service)
        node_set.add(d.target_service)
        total = d.request_count or 0
        errors = d.error_count or 0
        edges.append({
            "source":        d.source_service,
            "target":        d.target_service,
            "request_count": total,
            "error_count":   errors,
            "error_rate":    round(errors / total, 4) if total > 0 else 0.0,
        })
    return {
        "nodes": sorted(node_set),
        "edges": edges,
    }


def _build_anomaly_list(anomalies: list[Anomaly]) -> list[dict[str, Any]]:
    return [
        {
            "service_name":   a.service_name,
            "metric_name":    a.metric_name,
            "z_score":        a.z_score,
            "direction":      a.direction,
            "current_value":  a.current_value,
            "baseline_mean":  a.baseline_mean,
            "description":    a.description,
        }
        for a in anomalies
    ]


# ── Main entry point ───────────────────────────────────────────────────────────

async def assemble_evidence(
    db: AsyncSession,
    incident_id: int,
) -> dict[str, Any] | None:
    """
    Assemble the complete evidence context for an incident.

    Returns None if the incident does not exist.
    Returns a structured dict that is ready to be JSON-serialised and
    injected into the Groq prompt as the user message.
    """
    inc = await _load_incident(db, incident_id)
    if inc is None:
        return None

    affected = inc.affected_services or []
    rca      = await _load_rca(db, incident_id)

    # If RCA hasn't been run, use the incident's affected services as a fallback
    rca_dict: dict[str, Any]
    if rca:
        rca_dict = {
            "root_cause_service": rca.root_cause_service,
            "confidence":         rca.confidence,
            "propagation_path":   rca.propagation_path,
            "candidate_scores":   rca.candidate_scores,
        }
        # Expand services to include the full propagation path
        all_services = list({*affected, *rca.propagation_path})
    else:
        rca_dict     = {"root_cause_service": affected[0] if affected else "unknown",
                        "confidence": 0.0, "propagation_path": affected, "candidate_scores": {}}
        all_services = affected

    anomalies   = await _load_anomalies(db, all_services)
    deps        = await _load_graph_subgraph(db, all_services)
    error_spans = await _load_error_spans(db, all_services)
    error_logs  = await _load_error_logs(db, all_services)

    return {
        # ── Incident ────────────────────────────────────────────────────────
        "incident": {
            "id":               inc.id,
            "title":            inc.title,
            "severity":         inc.severity,
            "status":           inc.status,
            "affected_services": affected,
            "triggered_by_rule": inc.triggered_by_rule,
            "description":      inc.description,
        },

        # ── Root cause analysis ─────────────────────────────────────────────
        "rca": rca_dict,

        # ── Statistical anomalies ────────────────────────────────────────────
        "anomalies": _build_anomaly_list(anomalies),

        # ── Service graph (1-hop subgraph) ───────────────────────────────────
        "service_graph": _build_graph_dict(deps, all_services),

        # ── Telemetry evidence ────────────────────────────────────────────────
        "error_spans": error_spans,
        "error_logs":  error_logs,

        # ── Meta ──────────────────────────────────────────────────────────────
        "_meta": {
            "anomaly_count":    len(anomalies),
            "error_span_count": len(error_spans),
            "error_log_count":  len(error_logs),
            "graph_node_count": len(deps) and len({d.source_service for d in deps} |
                                                   {d.target_service for d in deps}),
            "rca_available":    rca is not None,
        },
    }
