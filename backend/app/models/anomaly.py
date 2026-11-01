"""
FaultLens Backend — Anomaly ORM Model (Phase 12)

Stores detected metric anomalies computed by the Z-score engine.
One row per active (service, metric_name) anomaly.

When an anomaly is resolved (Z-score returns to normal),
is_active is set to False — the row stays for history.
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger, Boolean, Column, Float, Integer,
    String, Text, Index, UniqueConstraint,
)

from app.db.session import Base


class Anomaly(Base):
    """
    Detected metric anomaly from the statistical Z-score engine.

    Lifecycle:
      detected   → is_active=True,  resolved_at=None
      resolved   → is_active=False, resolved_at=<timestamp_ns>
    """
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Identity ───────────────────────────────────────────────────────────
    service_name = Column(String(256), nullable=False, index=True)
    metric_name  = Column(String(512), nullable=False, index=True)

    # ── Statistical values ─────────────────────────────────────────────────
    z_score          = Column(Float, nullable=False)
    baseline_mean    = Column(Float, nullable=False)
    baseline_stddev  = Column(Float, nullable=False)
    current_value    = Column(Float, nullable=False)
    # "spike" (value >> baseline) or "drop" (value << baseline)
    direction        = Column(String(8), nullable=False)

    # ── Time ───────────────────────────────────────────────────────────────
    # Epoch nanoseconds — consistent with all other tables
    detected_at_unix_nano  = Column(BigInteger, nullable=False)
    resolved_at_unix_nano  = Column(BigInteger, nullable=True)
    # Last scan in which this anomaly was still firing (drives the resolve cool-down)
    last_firing_unix_nano  = Column(BigInteger, nullable=True)

    # ── State ──────────────────────────────────────────────────────────────
    is_active  = Column(Boolean, nullable=False, default=True)

    # Short description for the AI context window
    description = Column(Text, nullable=True)

    __table_args__ = (
        # One active anomaly per (service, metric) pair at a time
        Index("ix_anomalies_service_metric", "service_name", "metric_name"),
        Index("ix_anomalies_active",         "is_active"),
        Index("ix_anomalies_detected",       "detected_at_unix_nano"),
    )
