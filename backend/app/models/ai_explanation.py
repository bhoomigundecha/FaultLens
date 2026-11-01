"""
FaultLens Backend — AI Explanation ORM Model (Phase 17)

Stores the Groq-generated explanation for one incident.
One row per incident — re-running POST overwrites it.
"""
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.db.session import Base


class AIExplanation(Base):
    """Groq-generated natural language explanation for an incident."""

    __tablename__ = "ai_explanations"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, nullable=False, unique=True, index=True)

    # ── AI output fields (matching the JSON schema) ────────────────────────
    root_cause_service = Column(String(256), nullable=False)
    fault_type         = Column(String(256), nullable=False)
    confidence_label   = Column(String(16),  nullable=False)   # high/medium/low
    propagation_path   = Column(JSONB,       nullable=False, default=list)
    human_summary      = Column(Text,        nullable=False)
    remediation_steps  = Column(JSONB,       nullable=False, default=list)

    # ── Metadata ────────────────────────────────────────────────────────────
    model        = Column(String(128), nullable=True)   # e.g. "llama-3.3-70b-versatile"
    ai_available = Column(Boolean,     nullable=False, default=False)

    generated_at_unix_nano = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("incident_id", name="uq_ai_explanation_incident"),
        Index("ix_ai_explanation_incident", "incident_id"),
    )
