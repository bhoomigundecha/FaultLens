"""
FaultLens Backend — Service ORM Model (Phase 9)

Tracks every unique service seen in incoming telemetry.
Automatically upserted by the ingestion pipeline whenever a new
service name appears in spans, metrics, or log records.
"""
from __future__ import annotations

from sqlalchemy import BigInteger, Column, Integer, String, Index

from app.db.session import Base


class Service(Base):
    """
    One row per unique service.name observed in telemetry.

    Counters are updated incrementally at ingest time — no full table
    scans needed to compute overview metrics.
    """
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # The canonical service identifier (from resource attribute service.name)
    name = Column(String(256), nullable=False, unique=True, index=True)

    # Epoch nanoseconds of the earliest and most recent telemetry seen
    first_seen_unix_nano = Column(BigInteger, nullable=False)
    last_seen_unix_nano  = Column(BigInteger, nullable=False)

    # Cumulative counters — spans where status_code != 2 are "requests",
    # spans where status_code == 2 (ERROR) increment error_count.
    request_count = Column(BigInteger, nullable=False, default=0)
    error_count   = Column(BigInteger, nullable=False, default=0)

    __table_args__ = (
        Index("ix_services_last_seen", "last_seen_unix_nano"),
    )
