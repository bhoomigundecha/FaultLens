"""
LangGraph shared state — the single TypedDict that flows through all agent nodes.

All agents read from and write to this state.
Pydantic-annotated fields use reducers for list accumulation.
"""

from __future__ import annotations

from typing import Annotated, Any
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class FaultLensState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────────────
    service_id:       str
    incident_id:      str
    environment_type: str    # rich / medium / thin / unknown

    # ── Evidence collected by agents ──────────────────────────────────────────
    metric_anomalies:  list[dict[str, Any]]   # from AnomalyHunterAgent
    log_anomalies:     list[dict[str, Any]]   # from LogAnomalyAgent / AnomalyHunterAgent
    trace_anomalies:   list[dict[str, Any]]   # from GraphWeaverAgent

    # ── Fused score ───────────────────────────────────────────────────────────
    fused_score:       float
    fused_evidence:    str

    # ── Graph analysis ────────────────────────────────────────────────────────
    service_graph:     dict[str, Any]    # {nodes, edges} from Neo4j
    pagerank_scores:   dict[str, float]  # node_id → PR score
    causal_path:       list[str]         # ordered list of suspect service IDs

    # ── RCA output ────────────────────────────────────────────────────────────
    ranked_suspects:   list[dict[str, Any]]   # [{service_id, score, evidence}]
    failure_type:      str               # e.g. "AI_RATE_LIMIT_EXCEEDED"
    confidence:        float             # 0.0 → 1.0
    team_routing:      str               # "backend" / "infra" / "ml-platform"
    remediation_steps: list[str]         # concrete actionable fixes for this failure
    rca_report:        str               # final LLM-written markdown report

    # ── Agent control flow ────────────────────────────────────────────────────
    nodes_executed:    Annotated[list[str], lambda a, b: a + b]
    error:             str | None

    # ── LangGraph messages (for LLM reasoning chain) ──────────────────────────
    messages: Annotated[list[BaseMessage], add_messages]


def initial_state(service_id: str, incident_id: str) -> FaultLensState:
    """Create a blank state for a new agent run."""
    return FaultLensState(
        service_id=service_id,
        incident_id=incident_id,
        environment_type="unknown",
        metric_anomalies=[],
        log_anomalies=[],
        trace_anomalies=[],
        fused_score=0.0,
        fused_evidence="",
        service_graph={},
        pagerank_scores={},
        causal_path=[],
        ranked_suspects=[],
        failure_type="",
        confidence=0.0,
        team_routing="",
        remediation_steps=[],
        rca_report="",
        nodes_executed=[],
        error=None,
        messages=[],
    )
