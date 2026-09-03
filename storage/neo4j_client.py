"""
Neo4j client — maintains the service dependency graph and causal graph.

Node labels:
  - :Service   {id, name, env_type, last_seen}
  - :Database  {id, name, type}          (e.g. postgres, redis)
  - :Queue     {id, name}               (e.g. kafka topic)
  - :ExternalAPI {id, url}

Relationship types:
  - (:Service)-[:CALLS {latency_p99_ms, error_rate, last_updated}]->(:Service|:Database|:Queue|:ExternalAPI)
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_driver: Driver | None = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=10,
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver:
        _driver.close()
        _driver = None


@contextmanager
def get_session():
    driver = get_driver()
    with driver.session() as session:
        yield session


# ─── Schema / Constraints ─────────────────────────────────────────────────────

def init_schema() -> None:
    """Create uniqueness constraints and indexes. Idempotent."""
    with get_session() as s:
        s.run("CREATE CONSTRAINT service_id IF NOT EXISTS FOR (n:Service) REQUIRE n.id IS UNIQUE")
        s.run("CREATE CONSTRAINT db_id IF NOT EXISTS FOR (n:Database) REQUIRE n.id IS UNIQUE")
        s.run("CREATE CONSTRAINT queue_id IF NOT EXISTS FOR (n:Queue) REQUIRE n.id IS UNIQUE")
        s.run("CREATE CONSTRAINT ext_id IF NOT EXISTS FOR (n:ExternalAPI) REQUIRE n.id IS UNIQUE")
    logger.info("Neo4j schema constraints initialised")


# ─── Upserts ──────────────────────────────────────────────────────────────────

def upsert_service(service_id: str, name: str, env_type: str = "rich") -> None:
    with get_session() as s:
        s.run(
            """
            MERGE (svc:Service {id: $id})
            SET   svc.name     = $name,
                  svc.env_type = $env_type,
                  svc.last_seen = datetime()
            """,
            id=service_id,
            name=name,
            env_type=env_type,
        )


def upsert_edge(
    caller_id: str,
    callee_id: str,
    callee_type: str = "Service",
    *,
    latency_p99_ms: float | None = None,
    error_rate: float | None = None,
) -> None:
    """
    Create or update a CALLS relationship between two nodes.
    `callee_type` can be 'Service', 'Database', 'Queue', or 'ExternalAPI'.
    """
    with get_session() as s:
        s.run(
            f"""
            MERGE (a:Service {{id: $caller_id}})
            MERGE (b:{callee_type} {{id: $callee_id}})
            MERGE (a)-[r:CALLS]->(b)
            SET   r.last_updated    = datetime(),
                  r.latency_p99_ms  = CASE WHEN $latency IS NOT NULL THEN $latency ELSE r.latency_p99_ms END,
                  r.error_rate      = CASE WHEN $err IS NOT NULL THEN $err ELSE r.error_rate END
            """,
            caller_id=caller_id,
            callee_id=callee_id,
            latency=latency_p99_ms,
            err=error_rate,
        )


def set_node_anomaly_score(node_id: str, score: float) -> None:
    """Temporarily annotate a node with its current anomaly score (for PageRank seeding)."""
    with get_session() as s:
        s.run(
            "MATCH (n {id: $id}) SET n.anomaly_score = $score",
            id=node_id,
            score=score,
        )


# ─── Reads ────────────────────────────────────────────────────────────────────

def get_service_subgraph(service_id: str, depth: int = 3) -> dict[str, Any]:
    """
    Return the subgraph reachable from `service_id` up to `depth` hops.
    Returns: { nodes: [...], edges: [...] }
    """
    with get_session() as s:
        result = s.run(
            f"""
            MATCH path = (start {{id: $id}})-[:CALLS*1..{depth}]->(neighbor)
            UNWIND relationships(path) AS rel
            RETURN
                startNode(rel).id AS source,
                endNode(rel).id   AS target,
                labels(endNode(rel))[0] AS target_type,
                rel.latency_p99_ms  AS latency_p99_ms,
                rel.error_rate      AS error_rate,
                endNode(rel).anomaly_score AS target_anomaly_score
            """,
            id=service_id,
        )
        edges = [dict(r) for r in result]

    nodes = set()
    for e in edges:
        nodes.add(e["source"])
        nodes.add(e["target"])

    return {"nodes": list(nodes), "edges": edges}


def get_upstream_callers(service_id: str) -> list[str]:
    """Who calls this service? Useful for blast-radius analysis."""
    with get_session() as s:
        result = s.run(
            "MATCH (caller)-[:CALLS]->(svc {id: $id}) RETURN caller.id AS id",
            id=service_id,
        )
        return [r["id"] for r in result]


def get_downstream_callees(service_id: str) -> list[str]:
    """What does this service call? Useful for cascade analysis."""
    with get_session() as s:
        result = s.run(
            "MATCH (svc {id: $id})-[:CALLS]->(callee) RETURN callee.id AS id",
            id=service_id,
        )
        return [r["id"] for r in result]


def get_all_services() -> list[dict[str, Any]]:
    with get_session() as s:
        result = s.run("MATCH (svc:Service) RETURN svc.id AS id, svc.env_type AS env_type, svc.name AS name")
        return [dict(r) for r in result]


def run_pagerank(
    seeded_nodes: dict[str, float],
    iterations: int = 20,
) -> dict[str, float]:
    """
    Simple personalised PageRank over the service graph.
    `seeded_nodes` maps node_id → initial anomaly score (the teleport vector).
    Returns node_id → final PageRank score.
    """
    # First annotate the graph with seed scores
    for node_id, score in seeded_nodes.items():
        set_node_anomaly_score(node_id, score)

    with get_session() as s:
        # Use Neo4j GDS if available; fall back to manual Cypher implementation
        try:
            # Check if GDS plugin is available
            s.run("CALL gds.graph.exists('faultlens-graph') YIELD exists")
            use_gds = True
        except Exception:
            use_gds = False

        if use_gds:
            scores = _pagerank_gds(s, seeded_nodes)
        else:
            scores = _pagerank_cypher(s, seeded_nodes, iterations)

    return scores


def _pagerank_cypher(
    session: Session,
    seeded_nodes: dict[str, float],
    iterations: int,
) -> dict[str, float]:
    """
    Manual personalised PageRank — works without GDS plugin.
    Propagates anomaly scores backward through CALLS edges.
    """
    damping = 0.85
    scores: dict[str, float] = dict(seeded_nodes)

    for _ in range(iterations):
        result = session.run(
            """
            MATCH (a)-[:CALLS]->(b)
            WHERE a.anomaly_score IS NOT NULL OR b.anomaly_score IS NOT NULL
            RETURN a.id AS source, b.id AS target,
                   coalesce(a.anomaly_score, 0.0) AS source_score,
                   coalesce(b.anomaly_score, 0.0) AS target_score
            """
        )
        new_scores: dict[str, float] = {}
        for r in result:
            src, tgt = r["source"], r["target"]
            # Anomaly propagates upstream: if target is anomalous, source might be root
            new_scores[src] = new_scores.get(src, 0.0) + damping * r["target_score"]
            new_scores[tgt] = new_scores.get(tgt, r["target_score"])

        for node_id, score in new_scores.items():
            session.run(
                "MATCH (n {id: $id}) SET n.anomaly_score = $score",
                id=node_id, score=score,
            )
        scores.update(new_scores)

    return scores


def _pagerank_gds(session: Session, seeded_nodes: dict[str, float]) -> dict[str, float]:
    """Use Neo4j Graph Data Science plugin for PageRank (if installed)."""
    session.run(
        """
        CALL gds.graph.project.cypher(
            'faultlens-graph',
            'MATCH (n) RETURN id(n) AS id, coalesce(n.anomaly_score, 0.0) AS anomalyScore',
            'MATCH (a)-[:CALLS]->(b) RETURN id(a) AS source, id(b) AS target'
        )
        """
    )
    result = session.run(
        """
        CALL gds.pageRank.stream('faultlens-graph', {maxIterations: 20, dampingFactor: 0.85})
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).id AS node_id, score
        """
    )
    scores = {r["node_id"]: r["score"] for r in result}
    session.run("CALL gds.graph.drop('faultlens-graph')")
    return scores
