"""
Kafka/Redpanda topic definitions.

All topic names live here so changing a topic name is a one-line edit.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    name: str
    partitions: int = 3
    replication_factor: int = 1


# ─── Inbound raw signals ──────────────────────────────────────────────────────
RAW_METRICS = Topic("raw.metrics")
RAW_LOGS    = Topic("raw.logs")
RAW_TRACES  = Topic("raw.traces")

# ─── Processed events ─────────────────────────────────────────────────────────
ANOMALY_EVENTS = Topic("anomaly.events")   # produced by ML layer / consumers
RCA_RESULTS    = Topic("rca.results")      # produced by agent reporter

# ─── All topics (for auto-creation at startup) ────────────────────────────────
ALL_TOPICS: list[Topic] = [RAW_METRICS, RAW_LOGS, RAW_TRACES, ANOMALY_EVENTS, RCA_RESULTS]
