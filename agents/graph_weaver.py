"""
Graph Weaver Agent — Node 3 in the LangGraph workflow.

Responsibilities:
  1. Query Neo4j for the service dependency subgraph
  2. Annotate graph edges with current health state (error rates, latency)
  3. Detect trace-level anomalies (slow spans, error spans)
  4. Update state with service_graph and trace_anomalies
"""

from __future__ import annotations

import logging
from typing import Any

import storage.elasticsearch_client as es_store
import storage.neo4j_client as neo4j_store
from agents.state import FaultLensState
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# P99 latency threshold for flagging a span as slow (ms)
SLOW_SPAN_THRESHOLD_MS = 2000.0
ERROR_RATE_THRESHOLD   = 0.10   # 10%


async def graph_weaver_node(state: FaultLensState) -> dict[str, Any]:
    """LangGraph node: build/refresh service graph and detect trace anomalies."""
    service_id = state["service_id"]
    logger.info(f"[GraphWeaver] Building service graph for {service_id}")

    trace_anomalies: list[dict] = []
    service_graph: dict = {"nodes": [], "edges": []}

    # ── Pull service dependency graph from Neo4j ──────────────────────────────
    try:
        graph = neo4j_store.get_service_subgraph(service_id, depth=4)
        service_graph = graph

        # Detect anomalous edges (high latency or high error rate)
        for edge in graph.get("edges", []):
            lat = edge.get("latency_p99_ms") or 0.0
            err = edge.get("error_rate") or 0.0

            if lat > SLOW_SPAN_THRESHOLD_MS:
                trace_anomalies.append({
                    "type":           "slow_dependency",
                    "caller":         edge["source"],
                    "callee":         edge["target"],
                    "latency_ms":     lat,
                    "score":          min(1.0, lat / (SLOW_SPAN_THRESHOLD_MS * 2)),
                    "evidence":       f"p99 latency {lat:.0f}ms on {edge['source']}→{edge['target']} (threshold={SLOW_SPAN_THRESHOLD_MS}ms)",
                })

            if err > ERROR_RATE_THRESHOLD:
                trace_anomalies.append({
                    "type":       "high_error_rate",
                    "caller":     edge["source"],
                    "callee":     edge["target"],
                    "error_rate": err,
                    "score":      min(1.0, err * 5),
                    "evidence":   f"Error rate {err:.0%} on {edge['source']}→{edge['target']} (threshold={ERROR_RATE_THRESHOLD:.0%})",
                })

    except Exception as e:
        logger.warning(f"[GraphWeaver] Neo4j query failed: {e}")

    # ── If graph is empty, try to infer topology from logs ────────────────────
    if not service_graph.get("nodes"):
        try:
            logs = await es_store.get_logs_window(service_id, window_minutes=settings.metric_window_minutes)
            mentioned_services = _extract_mentioned_services(logs)
            for dep in mentioned_services:
                neo4j_store.upsert_service(dep, dep)
                neo4j_store.upsert_edge(service_id, dep)
            if mentioned_services:
                service_graph = neo4j_store.get_service_subgraph(service_id, depth=2)
                logger.info(f"[GraphWeaver] Inferred {len(mentioned_services)} dependencies from logs")
        except Exception as e:
            logger.warning(f"[GraphWeaver] Log-based topology inference failed: {e}")

    trace_score = max((a["score"] for a in trace_anomalies), default=None)

    # Update fused score to include trace evidence
    from ml.fusion import fuse_scores
    fused = fuse_scores(
        service_id=state["service_id"],
        env_type=state["environment_type"],
        metric_score=state.get("fused_score") or None,  # carry forward
        log_score=None,
        trace_score=trace_score,
    )

    logger.info(
        f"[GraphWeaver] {service_id}: {len(service_graph.get('nodes', []))} nodes, "
        f"{len(trace_anomalies)} trace anomalies"
    )

    return {
        "service_graph":    service_graph,
        "trace_anomalies":  trace_anomalies,
        "nodes_executed":   ["graph_weaver"],
    }


def _extract_mentioned_services(logs: list[dict]) -> list[str]:
    """
    Heuristic: scan log bodies for patterns like 'calling X', 'request to X',
    'timeout waiting for X' to infer upstream dependencies.
    """
    import re
    patterns = [
        r"calling\s+([a-z][a-z0-9\-]+(?:-service)?)",
        r"request\s+to\s+([a-z][a-z0-9\-]+(?:-service)?)",
        r"waiting\s+for\s+([a-z][a-z0-9\-]+(?:-service)?)",
        r"connect(?:ing|ion)?\s+to\s+([a-z][a-z0-9\-]+(?:-service|db)?)",
    ]
    found = set()
    for log in logs:
        body = log.get("body", "").lower()
        for pat in patterns:
            for match in re.finditer(pat, body):
                found.add(match.group(1))
    return list(found)
