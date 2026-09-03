"""
LangGraph workflow — wires all 6 agents into a directed graph.

Graph structure:
  START → signal_scout
            ├─(rich/medium)→ anomaly_hunter → graph_weaver → rca_investigator
            └─(thin)─────→ log_anomaly      ────────────→ rca_investigator
                                                              ↓
                                                           triage → reporter → END
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import StateGraph, END, START

from agents.state import FaultLensState
from agents.signal_scout import signal_scout_node
from agents.anomaly_hunter import anomaly_hunter_node
from agents.graph_weaver import graph_weaver_node
from agents.rca_investigator import rca_investigator_node
from agents.triage import triage_node
from agents.reporter import reporter_node

logger = logging.getLogger(__name__)


# ─── Log-only anomaly node (thin environment path) ────────────────────────────

async def log_anomaly_node(state: FaultLensState) -> dict:
    """
    Thin-environment shortcut: only runs log anomaly detection.
    Delegates to AnomalyHunter but skips metric analysis (no metrics available).
    Reuses anomaly_hunter_node — it gracefully skips missing signals.
    """
    return await anomaly_hunter_node(state)


# ─── Routing function ─────────────────────────────────────────────────────────

def route_by_environment(
    state: FaultLensState,
) -> Literal["anomaly_hunter", "log_anomaly_agent"]:
    """After signal_scout, pick the right analysis path."""
    env = state.get("environment_type", "unknown")
    if env in ("rich", "medium"):
        return "anomaly_hunter"
    return "log_anomaly_agent"


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph(checkpointer=None) -> StateGraph:
    """
    Build and compile the FaultLens LangGraph.

    Pass a checkpointer (e.g. AsyncPostgresSaver) to enable state persistence
    and resumability across agent runs.
    """
    builder = StateGraph(FaultLensState)

    # ── Register nodes ────────────────────────────────────────────────────────
    builder.add_node("signal_scout",     signal_scout_node)
    builder.add_node("anomaly_hunter",   anomaly_hunter_node)
    builder.add_node("log_anomaly_agent", log_anomaly_node)
    builder.add_node("graph_weaver",     graph_weaver_node)
    builder.add_node("rca_investigator", rca_investigator_node)
    builder.add_node("triage",           triage_node)
    builder.add_node("reporter",         reporter_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    builder.set_entry_point("signal_scout")

    # ── Conditional routing after signal_scout ────────────────────────────────
    builder.add_conditional_edges(
        "signal_scout",
        route_by_environment,
        {
            "anomaly_hunter":    "anomaly_hunter",
            "log_anomaly_agent": "log_anomaly_agent",
        },
    )

    # ── Rich/medium path ──────────────────────────────────────────────────────
    builder.add_edge("anomaly_hunter",   "graph_weaver")
    builder.add_edge("graph_weaver",     "rca_investigator")

    # ── Thin path ─────────────────────────────────────────────────────────────
    builder.add_edge("log_anomaly_agent", "rca_investigator")

    # ── Common tail ───────────────────────────────────────────────────────────
    builder.add_edge("rca_investigator", "triage")
    builder.add_edge("triage",           "reporter")
    builder.add_edge("reporter",          END)

    return builder.compile(checkpointer=checkpointer)


# ─── Convenience: run without a checkpointer (for testing) ───────────────────

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
