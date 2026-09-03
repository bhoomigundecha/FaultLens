"""
Base Kafka consumer — subclass this to build signal-type-specific consumers.

Each consumer runs in its own thread (via `start()`) and calls `handle(msg)`
for each message. Override `handle()` in subclasses.

Built-in consumers:
  - MetricsConsumer  → normalises + stores in TimescaleDB
  - LogsConsumer     → normalises + stores in Elasticsearch
  - TracesConsumer   → normalises + updates Neo4j
"""

from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any

from confluent_kafka import Consumer, KafkaError, KafkaException

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseConsumer(ABC):
    """
    Abstract Kafka consumer. Runs in a background daemon thread.
    Subclasses implement `handle(payload: dict)`.
    """

    def __init__(self, topics: list[str], group_id: str | None = None) -> None:
        self.topics = topics
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "group.id": group_id or settings.kafka_consumer_group,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 1000,
                "session.timeout.ms": 30000,
            }
        )

    @abstractmethod
    def handle(self, payload: dict[str, Any]) -> None:
        """Process a single decoded message payload."""

    def _run(self) -> None:
        self._consumer.subscribe(self.topics)
        logger.info(f"{self.__class__.__name__} subscribed to {self.topics}")
        try:
            while not self._stop_event.is_set():
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    self.handle(payload)
                except Exception as exc:
                    logger.exception(f"Error handling message from {msg.topic()}: {exc}")
        finally:
            self._consumer.close()

    def start(self) -> None:
        """Start the consumer in a background daemon thread."""
        self._thread = threading.Thread(target=self._run, daemon=True, name=self.__class__.__name__)
        self._thread.start()
        logger.info(f"{self.__class__.__name__} started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)


# ─── Concrete Consumers ───────────────────────────────────────────────────────

import asyncio
import storage.timescale as ts_store
import storage.elasticsearch_client as es_store
import storage.neo4j_client as neo4j_store
from pipeline.topics import RAW_METRICS, RAW_LOGS, RAW_TRACES


class MetricsConsumer(BaseConsumer):
    """Consumes raw.metrics → stores in TimescaleDB."""

    def __init__(self) -> None:
        super().__init__([RAW_METRICS.name], group_id="faultlens-metrics-store")

    def handle(self, payload: dict[str, Any]) -> None:
        # payload is a normalised metric dict (see ingestion/models.py)
        asyncio.run(ts_store.insert_metric(
            service_id=payload["service_id"],
            metric_name=payload["metric_name"],
            value=payload["value"],
            unit=payload.get("unit", ""),
            labels=payload.get("labels", {}),
        ))


class LogsConsumer(BaseConsumer):
    """Consumes raw.logs → stores in Elasticsearch."""

    def __init__(self) -> None:
        super().__init__([RAW_LOGS.name], group_id="faultlens-logs-store")

    def handle(self, payload: dict[str, Any]) -> None:
        asyncio.run(es_store.insert_log(payload))


class TracesConsumer(BaseConsumer):
    """Consumes raw.traces → updates Neo4j service dependency graph."""

    def __init__(self) -> None:
        super().__init__([RAW_TRACES.name], group_id="faultlens-traces-store")

    def handle(self, payload: dict[str, Any]) -> None:
        """
        Each trace payload contains a list of spans.
        We extract caller→callee relationships and upsert them in Neo4j.
        """
        spans = payload.get("spans", [])
        span_map = {s["span_id"]: s for s in spans}

        for span in spans:
            if not span.get("parent_span_id"):
                continue
            parent = span_map.get(span["parent_span_id"])
            if parent is None:
                continue
            caller_id = parent["service_id"]
            callee_id = span["service_id"]
            if caller_id == callee_id:
                continue

            duration_ms = span.get("duration_ms", 0)
            is_error = span.get("status_code") == "ERROR"

            neo4j_store.upsert_service(caller_id, caller_id)
            neo4j_store.upsert_service(callee_id, callee_id)
            neo4j_store.upsert_edge(
                caller_id=caller_id,
                callee_id=callee_id,
                latency_p99_ms=float(duration_ms),
                error_rate=1.0 if is_error else 0.0,
            )
