"""
Async Kafka producer — thin wrapper around confluent-kafka.

Usage:
    producer = get_producer()
    await producer.publish(RAW_METRICS.name, payload_dict)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from confluent_kafka import Producer, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

from config.settings import get_settings
from pipeline.topics import ALL_TOPICS

logger = logging.getLogger(__name__)
settings = get_settings()

_producer: Producer | None = None


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "acks": "1",                    # leader ack only — fast
                "linger.ms": 5,                 # micro-batch for throughput
                "batch.size": 32768,
                "compression.type": "snappy",
            }
        )
    return _producer


def _delivery_callback(err, msg) -> None:
    if err:
        logger.error(f"Kafka delivery failed: {err}")
    else:
        logger.debug(f"Delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")


def publish(topic: str, payload: dict[str, Any], key: str | None = None) -> None:
    """
    Fire-and-forget publish. Non-blocking.
    Call `flush()` at shutdown to drain the internal queue.
    """
    producer = get_producer()
    producer.produce(
        topic=topic,
        value=json.dumps(payload).encode("utf-8"),
        key=key.encode("utf-8") if key else None,
        callback=_delivery_callback,
    )
    producer.poll(0)  # trigger callbacks without blocking


def flush(timeout: float = 10.0) -> None:
    """Flush all pending messages. Call at graceful shutdown."""
    producer = get_producer()
    remaining = producer.flush(timeout)
    if remaining > 0:
        logger.warning(f"Kafka flush timed out with {remaining} messages undelivered")


# ─── Topic auto-creation ──────────────────────────────────────────────────────

def ensure_topics_exist() -> None:
    """Create all FaultLens topics if they don't already exist."""
    admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
    existing = set(admin.list_topics(timeout=10).topics.keys())

    to_create = [
        NewTopic(t.name, num_partitions=t.partitions, replication_factor=t.replication_factor)
        for t in ALL_TOPICS
        if t.name not in existing
    ]

    if not to_create:
        logger.info("All Kafka topics already exist")
        return

    futures = admin.create_topics(to_create)
    for topic_name, future in futures.items():
        try:
            future.result()
            logger.info(f"Created topic: {topic_name}")
        except Exception as e:
            if "TopicExistsException" not in str(e):
                logger.error(f"Failed to create topic {topic_name}: {e}")
