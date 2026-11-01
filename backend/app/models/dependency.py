"""
FaultLens Backend — Service Dependency ORM Model (Phase 10)

Stores directed service-to-service call relationships derived from
trace parent/child span relationships.

A dependency edge (source → target) means:
  "source_service made a call that created a span in target_service"

This is detected by finding spans where the parent span belongs to a
different service — a classic cross-service call in distributed tracing.
"""
from __future__ import annotations

from sqlalchemy import BigInteger, Column, Integer, String, Index, UniqueConstraint

from app.db.session import Base


class ServiceDependency(Base):
    """
    One row per directed service pair (source → target).

    Counters are incremented at ingest time via INSERT … ON CONFLICT DO UPDATE,
    giving O(1) writes and O(1) reads for the dependency graph.
    """
    __tablename__ = "service_dependencies"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # The calling service (parent span's service)
    source_service = Column(String(256), nullable=False, index=True)
    # The called service (child span's service)
    target_service = Column(String(256), nullable=False, index=True)

    # Time range this edge has been observed
    first_seen_unix_nano = Column(BigInteger, nullable=False)
    last_seen_unix_nano  = Column(BigInteger, nullable=False)

    # Call volume (one per cross-service child span)
    request_count = Column(BigInteger, nullable=False, default=0)
    # Calls where the child span had status_code == 2 (ERROR)
    error_count   = Column(BigInteger, nullable=False, default=0)

    __table_args__ = (
        # Each (source, target) pair is unique — conflicts trigger UPDATE
        UniqueConstraint("source_service", "target_service",
                         name="uq_service_dependencies_pair"),
        Index("ix_service_dep_source", "source_service"),
        Index("ix_service_dep_target", "target_service"),
    )
