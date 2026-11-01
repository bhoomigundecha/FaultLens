"""
FaultLens Backend — Incident ORM Model (Phase 13)

An Incident groups one or more active anomalies into a named,
severity-rated event that operators act on.

Lifecycle:  open → acknowledged → resolved
"""
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.db.session import Base


class Incident(Base):
    """
    A named, severity-rated operational event derived from anomalies.

    Created by the rule-based Incident Engine (Phase 13).
    Read by the AI Explanation Layer (Phase 17).
    """
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Identity ───────────────────────────────────────────────────────────
    title    = Column(String(512), nullable=False)
    severity = Column(String(16),  nullable=False)   # critical / high / medium / low
    status   = Column(String(16),  nullable=False, default="open")  # open / resolved

    # ── Scope ──────────────────────────────────────────────────────────────
    # List of service names affected, e.g. ["payment", "checkout"]
    affected_services = Column(JSONB, nullable=False, default=list)
    # IDs of Anomaly rows that triggered this incident
    anomaly_ids       = Column(JSONB, nullable=False, default=list)
    # Which rule fired (e.g. "HIGH_ERROR_RATE", "MULTI_SIGNAL", "LATENCY_SPIKE")
    triggered_by_rule = Column(String(64), nullable=True)

    # ── Summary for AI context ─────────────────────────────────────────────
    description = Column(Text, nullable=True)

    # ── Time ───────────────────────────────────────────────────────────────
    created_at_unix_nano  = Column(BigInteger, nullable=False)
    resolved_at_unix_nano = Column(BigInteger, nullable=True)

    __table_args__ = (
        Index("ix_incidents_status",   "status"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_created",  "created_at_unix_nano"),
    )
