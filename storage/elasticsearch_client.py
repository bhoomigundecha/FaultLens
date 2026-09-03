"""
Elasticsearch client — stores logs and incident reports.

Two indices:
  - faultlens-logs      : normalized log records with dense_vector for semantic search
  - faultlens-incidents : completed RCA reports, also vector-searchable
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level client (lazily initialised)
_client: AsyncElasticsearch | None = None

EMBEDDING_DIM = 768  # nomic-embed-text output dimension


def get_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = AsyncElasticsearch(
            hosts=[settings.elasticsearch_url],
            request_timeout=30,
            retry_on_timeout=True,
            max_retries=3,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client:
        await _client.close()
        _client = None


# ─── Index Mappings ───────────────────────────────────────────────────────────

LOGS_MAPPING = {
    "mappings": {
        "properties": {
            "timestamp":     {"type": "date"},
            "service_id":    {"type": "keyword"},
            "level":         {"type": "keyword"},
            "body":          {"type": "text", "analyzer": "standard"},
            "template_id":   {"type": "keyword"},
            "template":      {"type": "keyword"},
            "trace_id":      {"type": "keyword"},
            "span_id":       {"type": "keyword"},
            "attributes":    {"type": "object", "dynamic": True},
            "embedding": {
                "type": "dense_vector",
                "dims": EMBEDDING_DIM,
                "index": True,
                "similarity": "cosine",
            },
        }
    },
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
}

INCIDENTS_MAPPING = {
    "mappings": {
        "properties": {
            "incident_id":   {"type": "keyword"},
            "service_id":    {"type": "keyword"},
            "failure_type":  {"type": "keyword"},
            "confidence":    {"type": "float"},
            "report":        {"type": "text"},
            "ranked_suspects": {"type": "object", "dynamic": True},
            "created_at":    {"type": "date"},
            "resolved_at":   {"type": "date"},
            "embedding": {
                "type": "dense_vector",
                "dims": EMBEDDING_DIM,
                "index": True,
                "similarity": "cosine",
            },
        }
    },
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
}


async def init_indices() -> None:
    """Create ES indices if they don't exist. Idempotent."""
    es = get_client()
    for index, mapping in [
        (settings.es_logs_index, LOGS_MAPPING),
        (settings.es_incidents_index, INCIDENTS_MAPPING),
    ]:
        exists = await es.indices.exists(index=index)
        if not exists:
            await es.indices.create(index=index, body=mapping)
            logger.info(f"Created Elasticsearch index: {index}")
        else:
            logger.debug(f"Elasticsearch index already exists: {index}")


# ─── Log Writes ───────────────────────────────────────────────────────────────

async def insert_log(log: dict[str, Any]) -> None:
    """Index a single normalised log record."""
    es = get_client()
    await es.index(index=settings.es_logs_index, document=log)


async def insert_logs_batch(logs: list[dict[str, Any]]) -> None:
    """Bulk-index log records."""
    from elasticsearch.helpers import async_bulk

    es = get_client()
    actions = [{"_index": settings.es_logs_index, "_source": log} for log in logs]
    await async_bulk(es, actions, raise_on_error=False)


# ─── Log Reads ────────────────────────────────────────────────────────────────

async def get_logs_window(
    service_id: str,
    window_minutes: int = 15,
    level: str | None = None,
) -> list[dict[str, Any]]:
    """Return recent logs for a service, optionally filtered by severity level."""
    es = get_client()
    must: list[dict] = [
        {"term": {"service_id": service_id}},
        {"range": {"timestamp": {"gte": f"now-{window_minutes}m"}}},
    ]
    if level:
        must.append({"term": {"level": level.upper()}})

    resp = await es.search(
        index=settings.es_logs_index,
        body={
            "query": {"bool": {"must": must}},
            "sort": [{"timestamp": "asc"}],
            "size": 1000,
        },
    )
    return [hit["_source"] for hit in resp["hits"]["hits"]]


async def get_error_log_count(service_id: str, window_minutes: int = 15) -> int:
    """Count ERROR/CRITICAL logs in the time window (fast metric for anomaly detection)."""
    es = get_client()
    resp = await es.count(
        index=settings.es_logs_index,
        body={
            "query": {
                "bool": {
                    "must": [
                        {"term": {"service_id": service_id}},
                        {"terms": {"level": ["ERROR", "CRITICAL", "FATAL"]}},
                        {"range": {"timestamp": {"gte": f"now-{window_minutes}m"}}},
                    ]
                }
            }
        },
    )
    return resp["count"]


async def semantic_search_logs(
    embedding: list[float],
    service_id: str | None = None,
    k: int = 10,
) -> list[dict[str, Any]]:
    """KNN search against log embeddings to find semantically similar log patterns."""
    es = get_client()
    filter_clause = []
    if service_id:
        filter_clause.append({"term": {"service_id": service_id}})

    resp = await es.search(
        index=settings.es_logs_index,
        body={
            "knn": {
                "field": "embedding",
                "query_vector": embedding,
                "k": k,
                "num_candidates": k * 5,
                "filter": filter_clause or None,
            }
        },
    )
    return [hit["_source"] for hit in resp["hits"]["hits"]]


# ─── Incident Writes / Reads ──────────────────────────────────────────────────

async def insert_incident(incident: dict[str, Any]) -> None:
    es = get_client()
    await es.index(
        index=settings.es_incidents_index,
        id=incident.get("incident_id"),
        document=incident,
    )


async def search_similar_incidents(
    embedding: list[float], k: int = 5
) -> list[dict[str, Any]]:
    """Find historically similar incidents using KNN on incident embeddings."""
    es = get_client()
    resp = await es.search(
        index=settings.es_incidents_index,
        body={
            "knn": {
                "field": "embedding",
                "query_vector": embedding,
                "k": k,
                "num_candidates": k * 5,
            }
        },
    )
    return [hit["_source"] for hit in resp["hits"]["hits"]]
