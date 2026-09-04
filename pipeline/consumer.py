"""
Kafka consumers — each runs in its own background daemon thread with a
dedicated asyncio event loop and its own DB connections.

This avoids the asyncpg/elasticsearch pool-vs-event-loop conflict that occurs
when sharing module-level async pools across threads.

Built-in consumers:
  - MetricsConsumer  → TimescaleDB (asyncpg direct connection)
  - LogsConsumer     → Elasticsearch (per-thread AsyncElasticsearch client)
  - TracesConsumer   → Neo4j (sync driver, safe from any thread)
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any

from confluent_kafka import Consumer, KafkaError

from config.settings import get_settings
from pipeline.topics import RAW_METRICS, RAW_LOGS, RAW_TRACES

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseConsumer(ABC):
    """
    Abstract Kafka consumer. Each instance runs in its own daemon thread
    with a dedicated asyncio event loop so there are zero shared async
    resources between threads.
    """

    def __init__(self, topics: list[str], group_id: str) -> None:
        self.topics = topics
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._consumer = Consumer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 1000,
            "session.timeout.ms": 30000,
        })

    @abstractmethod
    async def setup(self) -> None:
        """Called once at thread startup to initialise connections."""

    @abstractmethod
    async def handle(self, payload: dict[str, Any]) -> None:
        """Process one decoded Kafka message."""

    @abstractmethod
    async def teardown(self) -> None:
        """Called at thread shutdown to close connections."""

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.setup())
        except Exception:
            logger.exception(f"{self.__class__.__name__} setup failed")
            return

        self._consumer.subscribe(self.topics)
        logger.info(f"{self.__class__.__name__} subscribed to {self.topics}")

        try:
            while not self._stop_event.is_set():
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"{self.__class__.__name__} Kafka error: {msg.error()}")
                    continue
                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    loop.run_until_complete(self.handle(payload))
                except Exception:
                    logger.exception(f"{self.__class__.__name__} failed to handle message")
        finally:
            self._consumer.close()
            try:
                loop.run_until_complete(self.teardown())
            except Exception:
                pass
            loop.close()

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=self.__class__.__name__
        )
        self._thread.start()
        logger.info(f"{self.__class__.__name__} started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)


# ─── MetricsConsumer ─────────────────────────────────────────────────────────

class MetricsConsumer(BaseConsumer):
    """Consumes raw.metrics → inserts into TimescaleDB."""

    def __init__(self) -> None:
        super().__init__([RAW_METRICS.name], group_id="faultlens-metrics-store")
        self._conn = None

    async def setup(self) -> None:
        import asyncpg
        dsn = (
            settings.timescale_sync_url
            .replace("postgresql+asyncpg://", "postgresql://")
            .replace("postgresql+psycopg2://", "postgresql://")
        )
        self._conn = await asyncpg.connect(dsn)
        logger.info("MetricsConsumer: TimescaleDB connection ready")

    async def handle(self, payload: dict[str, Any]) -> None:
        from datetime import datetime, timezone
        ts_str = payload.get("timestamp")
        ts = (
            datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts_str else datetime.now(timezone.utc)
        )
        await self._conn.execute(
            """
            INSERT INTO metrics (time, service_id, metric_name, value, unit, labels)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            ts,
            payload["service_id"],
            payload["metric_name"],
            float(payload["value"]),
            payload.get("unit", ""),
            json.dumps(payload.get("labels", {})),
        )

    async def teardown(self) -> None:
        if self._conn:
            await self._conn.close()


# ─── LogsConsumer ─────────────────────────────────────────────────────────────

class LogsConsumer(BaseConsumer):
    """Consumes raw.logs → indexes into Elasticsearch."""

    def __init__(self) -> None:
        super().__init__([RAW_LOGS.name], group_id="faultlens-logs-store")
        self._es = None

    async def setup(self) -> None:
        from elasticsearch import AsyncElasticsearch
        self._es = AsyncElasticsearch(
            hosts=[settings.elasticsearch_url],
            request_timeout=30,
            retry_on_timeout=True,
            max_retries=3,
        )
        logger.info("LogsConsumer: Elasticsearch client ready")

    async def handle(self, payload: dict[str, Any]) -> None:
        await self._es.index(index=settings.es_logs_index, document=payload)

    async def teardown(self) -> None:
        if self._es:
            await self._es.close()


# ─── TracesConsumer ───────────────────────────────────────────────────────────

class TracesConsumer(BaseConsumer):
    """Consumes raw.traces → upserts edges in Neo4j service dependency graph."""

    def __init__(self) -> None:
        super().__init__([RAW_TRACES.name], group_id="faultlens-traces-store")

    async def setup(self) -> None:
        # Neo4j driver is sync — nothing async to set up
        logger.info("TracesConsumer: Neo4j driver ready (sync)")

    async def handle(self, payload: dict[str, Any]) -> None:
        import storage.neo4j_client as neo4j_store
        spans = payload.get("spans", [])
        span_map = {s["span_id"]: s for s in spans}

        for span in spans:
            parent_id = span.get("parent_span_id")
            if not parent_id:
                continue
            parent = span_map.get(parent_id)
            if parent is None:
                continue
            caller_id = parent["service_id"]
            callee_id = span["service_id"]
            if caller_id == callee_id:
                continue

            neo4j_store.upsert_service(caller_id, caller_id)
            neo4j_store.upsert_service(callee_id, callee_id)
            neo4j_store.upsert_edge(
                caller_id=caller_id,
                callee_id=callee_id,
                latency_p99_ms=float(span.get("duration_ms", 0)),
                error_rate=1.0 if span.get("status_code") == "ERROR" else 0.0,
            )

    async def teardown(self) -> None:
        pass
