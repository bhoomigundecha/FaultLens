"""
FaultLens Backend — Root Cause Analysis ORM Model (Phase 14)

Stores the result of one RCA run for an incident.
One row per incident — updated each time the RCA engine re-runs.

Read by the AI Explanation Layer (Phase 17) to build its context.
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger, Column, Float, Integer, String, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.session import Base


class RootCauseAnalysis(Base):
    """
    Result of a backward graph-traversal RCA for one incident.

    Fields
    ──────
    root_cause_service  The service identified as the fault origin.
    confidence          0.0–1.0 score: 1.0 = no anomalous upstream callers.
    propagation_path    Ordered list of services [root_cause → ... → victim].
    candidate_scores    {service_name: score} for all evaluated candidates.
    algorithm           The algorithm that produced this result.
    """
    __tablename__ = "root_cause_analyses"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, nullable=False, index=True)

    root_cause_service = Column(String(256), nullable=False)
    confidence         = Column(Float,       nullable=False)

    # JSON arrays / objects for AI context
    propagation_path  = Column(JSONB, nullable=False, default=list)
    candidate_scores  = Column(JSONB, nullable=False, default=dict)

    algorithm          = Column(String(64), nullable=False,
                                default="backward_graph_traversal")

    created_at_unix_nano = Column(BigInteger, nullable=False)

    __table_args__ = (
        # One RCA result per incident (latest overwrites)
        UniqueConstraint("incident_id", name="uq_rca_incident"),
        Index("ix_rca_incident",       "incident_id"),
        Index("ix_rca_root_cause_svc", "root_cause_service"),
    )
