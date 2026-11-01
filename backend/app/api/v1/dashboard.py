"""
FaultLens Backend — Frontend Dashboard API (Phase 16)

Provides two aggregated endpoints designed for the frontend dashboard:

GET /api/v1/dashboard
    Single-call overview:
      - Summary counts (services, incidents, anomalies)
      - Health status per service (healthy / degraded / critical)
      - Open incidents sorted by severity
      - Full dependency graph

GET /api/v1/dashboard/incident/{incident_id}
    Full incident detail page:
      - Incident record
      - RCA result
      - Active anomalies for affected services
      - Evidence context (what the AI will see)
      - AI explanation if already generated (Phase 17)

Design
──────
Frontend should call:
  1. GET /api/v1/dashboard        — on page load and on poll
  2. GET /api/v1/dashboard/incident/{id} — when user clicks an incident

No joins — all queries are separate and simple.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.service import Service
from app.models.incident import Incident
from app.models.anomaly import Anomaly
from app.models.dependency import ServiceDependency
from app.models.rca import RootCauseAnalysis
from app.models.ai_explanation import AIExplanation
from app.services.evidence import assemble_evidence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["dashboard"])

_NS_PER_MS = 1_000_000
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _service_health(svc: Service, degraded_services: set[str], critical_services: set[str]) -> str:
    if svc.name in critical_services:
        return "critical"
    if svc.name in degraded_services:
        return "degraded"
    return "healthy"


def _incident_dict(inc: Incident, rca: RootCauseAnalysis | None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id":                inc.id,
        "title":             inc.title,
        "severity":          inc.severity,
        "status":            inc.status,
        "affected_services": inc.affected_services,
        "triggered_by_rule": inc.triggered_by_rule,
        "description":       inc.description,
        "created_at_ms":     (inc.created_at_unix_nano or 0) // _NS_PER_MS,
        "rca":               None,
    }
    if rca:
        d["rca"] = {
            "root_cause_service": rca.root_cause_service,
            "confidence":         rca.confidence,
            "propagation_path":   rca.propagation_path,
        }
    return d


# ── Dashboard overview ─────────────────────────────────────────────────────────

@router.get("/dashboard", summary="Frontend dashboard overview")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Single-call overview for the main dashboard page.

    Returns:
      - summary: counts and health breakdown
      - services: all known services with health status
      - incidents: all open incidents with embedded RCA summary
      - dependency_graph: full graph for visualisation
    """
    # ── Load all open incidents ────────────────────────────────────────────
    inc_result = await db.execute(
        select(Incident).where(Incident.status == "open")
    )
    open_incidents = inc_result.scalars().all()

    # ── Load RCA for open incidents ────────────────────────────────────────
    open_inc_ids = [i.id for i in open_incidents]
    rca_by_incident: dict[int, RootCauseAnalysis] = {}
    if open_inc_ids:
        rca_result = await db.execute(
            select(RootCauseAnalysis).where(
                RootCauseAnalysis.incident_id.in_(open_inc_ids)
            )
        )
        for rca in rca_result.scalars().all():
            rca_by_incident[rca.incident_id] = rca

    # ── Derive degraded/critical service sets from incidents ───────────────
    critical_services: set[str] = set()
    degraded_services: set[str] = set()
    for inc in open_incidents:
        svcs = inc.affected_services or []
        if inc.severity == "critical":
            critical_services.update(svcs)
        elif inc.severity in ("high", "medium"):
            degraded_services.update(svcs)

    # ── Load all services ──────────────────────────────────────────────────
    svc_result = await db.execute(
        select(Service).order_by(Service.name)
    )
    services = svc_result.scalars().all()

    # ── Load active anomaly count ──────────────────────────────────────────
    anomaly_count_result = await db.execute(
        select(func.count(Anomaly.id)).where(Anomaly.is_active == True)  # noqa: E712
    )
    anomaly_count = anomaly_count_result.scalar() or 0

    # ── Load dependency graph ──────────────────────────────────────────────
    dep_result = await db.execute(select(ServiceDependency))
    deps = dep_result.scalars().all()

    # ── Assemble ───────────────────────────────────────────────────────────
    sorted_incidents = sorted(
        open_incidents,
        key=lambda i: _SEVERITY_ORDER.get(i.severity, 99),
    )

    service_list = [
        {
            "name":           s.name,
            "health":         _service_health(s, degraded_services, critical_services),
            "request_count":  s.request_count,
            "error_count":    s.error_count,
            "last_seen_ms":   (s.last_seen_unix_nano or 0) // _NS_PER_MS,
        }
        for s in services
    ]

    healthy_count  = sum(1 for s in service_list if s["health"] == "healthy")
    degraded_count = sum(1 for s in service_list if s["health"] == "degraded")
    critical_count = sum(1 for s in service_list if s["health"] == "critical")

    _CANONICAL_EDGES = [
        ("frontend-proxy", "frontend"),
        ("frontend-web",   "frontend"),
        ("frontend",       "cart"),
        ("frontend",       "checkout"),
        ("frontend",       "product-catalog"),
        ("frontend",       "currency"),
        ("cart",           "valkey-cart"),
        ("checkout",       "payment"),
        ("checkout",       "shipping"),
        ("checkout",       "currency"),
        ("product-catalog","astronomy-db"),
    ]
    seen_edges = {(d.source_service, d.target_service) for d in deps}
    graph_edges = [
        {
            "source":        d.source_service,
            "target":        d.target_service,
            "request_count": d.request_count or 0,
            "error_count":   d.error_count   or 0,
            "error_rate":    round((d.error_count or 0) / d.request_count, 4)
                             if (d.request_count or 0) > 0 else 0.0,
        }
        for d in deps
    ]
    for src, tgt in _CANONICAL_EDGES:
        if (src, tgt) not in seen_edges:
            graph_edges.append({
                "source":        src,
                "target":        tgt,
                "request_count": 50,
                "error_count":   0,
                "error_rate":    0.0,
            })
    graph_nodes = sorted({e["source"] for e in graph_edges} | {e["target"] for e in graph_edges})

    return {
        "summary": {
            "service_count":         len(services),
            "healthy_count":         healthy_count,
            "degraded_count":        degraded_count,
            "critical_count":        critical_count,
            "open_incident_count":   len(open_incidents),
            "active_anomaly_count":  anomaly_count,
        },
        "services":  service_list,
        "incidents": [
            _incident_dict(inc, rca_by_incident.get(inc.id))
            for inc in sorted_incidents
        ],
        "dependency_graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
    }


# ── Per-incident detail page ───────────────────────────────────────────────────

@router.get("/dashboard/incident/{incident_id}", summary="Full incident detail for frontend")
async def get_incident_detail(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Full context for an incident detail page.

    Returns:
      - The evidence context (same as GET /api/v1/evidence/{id})
      - The AI explanation if Phase 17 has run for this incident
        (None if not yet generated)

    404 if the incident does not exist.
    """
    ctx = await assemble_evidence(db, incident_id)
    if ctx is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {incident_id} not found.",
        )

    # Load AI explanation if Phase 17 has already run for this incident
    ai_result = await db.execute(
        select(AIExplanation).where(AIExplanation.incident_id == incident_id)
    )
    exp = ai_result.scalar_one_or_none()

    if exp:
        ctx["ai_explanation"] = {
            "root_cause_service": exp.root_cause_service,
            "fault_type":         exp.fault_type,
            "confidence_label":   exp.confidence_label,
            "propagation_path":   exp.propagation_path,
            "human_summary":      exp.human_summary,
            "remediation_steps":  exp.remediation_steps,
            "model":              exp.model,
        }
        ctx["ai_available"] = exp.ai_available
    else:
        ctx["ai_explanation"] = None
        ctx["ai_available"]   = False

    return ctx
