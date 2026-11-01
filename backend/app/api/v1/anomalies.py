"""
FaultLens Backend — Anomaly Detection API (Phase 12)

POST /api/v1/anomalies/scan
    Triggers a fresh Z-score scan across all known (service, metric) pairs.
    Returns the scan summary + list of detected anomalies.

GET /api/v1/anomalies
    Returns currently active anomalies (is_active=True), most severe first.

GET /api/v1/anomalies/history
    Returns all anomalies (active + resolved), most recent first.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.anomaly import Anomaly
from app.services.anomaly import run_anomaly_scan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["anomalies"])

_NS_PER_MS = 1_000_000


def _anomaly_to_dict(a: Anomaly) -> dict[str, Any]:
    return {
        "id":             a.id,
        "service_name":   a.service_name,
        "metric_name":    a.metric_name,
        "z_score":        a.z_score,
        "direction":      a.direction,
        "current_value":  a.current_value,
        "baseline_mean":  a.baseline_mean,
        "baseline_stddev": a.baseline_stddev,
        "description":    a.description,
        "is_active":      a.is_active,
        "detected_at_ms": (a.detected_at_unix_nano or 0) // _NS_PER_MS,
        "resolved_at_ms": (a.resolved_at_unix_nano // _NS_PER_MS
                           if a.resolved_at_unix_nano else None),
    }


@router.post("/anomalies/scan", summary="Run Z-score anomaly scan")
async def trigger_scan(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Runs the full Z-score anomaly detection scan on demand.

    This is the entry point for the statistical layer described in the
    research papers (GALA, RCAgent). Results are persisted to the anomalies
    table and consumed by the Phase 13 Incident Engine.

    Typical call cadence: every 1–5 minutes via a cron or after ingest.
    """
    result = await run_anomaly_scan(db)
    await db.commit()
    return result


@router.get("/anomalies", summary="Get currently active anomalies")
async def list_active_anomalies(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns only currently active anomalies, ordered by absolute Z-score
    descending (most severe first).

    This is what the Phase 13 Incident Engine reads.
    """
    result = await db.execute(
        select(Anomaly)
        .where(Anomaly.is_active == True)  # noqa: E712
        .order_by(Anomaly.z_score.desc())
    )
    anomalies = result.scalars().all()

    return {
        "anomalies": [_anomaly_to_dict(a) for a in anomalies],
        "total":     len(anomalies),
    }


@router.get("/anomalies/history", summary="Get anomaly history (active + resolved)")
async def list_anomaly_history(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns all anomalies including resolved ones, most recently detected first.
    Useful for post-incident review.
    """
    result = await db.execute(
        select(Anomaly)
        .order_by(Anomaly.detected_at_unix_nano.desc())
        .limit(200)
    )
    anomalies = result.scalars().all()

    return {
        "anomalies": [_anomaly_to_dict(a) for a in anomalies],
        "total":     len(anomalies),
    }
