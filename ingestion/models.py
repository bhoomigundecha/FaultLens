"""
Internal normalised data models.

All signals — regardless of source (OTLP, Vercel webhook, Render log drain)
— are converted into these Pydantic models before being published to Kafka.
This keeps the pipeline + agents decoupled from the ingestion format.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EnvironmentType(str, Enum):
    RICH   = "rich"    # OTel metrics + logs + traces
    MEDIUM = "medium"  # logs + traces only (some OTel, no custom metrics)
    THIN   = "thin"    # logs only (platform logs, response codes)
    UNKNOWN = "unknown"


class NormalizedMetric(BaseModel):
    """One data point for a single metric."""
    service_id:  str
    metric_name: str
    value:       float
    unit:        str = ""
    labels:      dict[str, Any] = Field(default_factory=dict)
    timestamp:   datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_kafka_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class NormalizedLog(BaseModel):
    """One log record, normalised from any source."""
    service_id:  str
    level:       str = "INFO"          # DEBUG / INFO / WARN / ERROR / CRITICAL
    body:        str
    timestamp:   datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id:    str = ""
    span_id:     str = ""
    template_id: str | None = None     # set after DRAIN3 parsing
    template:    str | None = None
    attributes:  dict[str, Any] = Field(default_factory=dict)
    embedding:   list[float] | None = None  # set after embedding

    @field_validator("level", mode="before")
    @classmethod
    def normalise_level(cls, v: str) -> str:
        mapping = {
            "trace": "DEBUG", "debug": "DEBUG",
            "info": "INFO", "information": "INFO",
            "warn": "WARN", "warning": "WARN",
            "error": "ERROR", "err": "ERROR",
            "critical": "CRITICAL", "fatal": "CRITICAL",
        }
        return mapping.get(str(v).lower(), str(v).upper())

    def to_kafka_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"embedding"})


class NormalizedSpan(BaseModel):
    """One span from a distributed trace."""
    trace_id:       str
    span_id:        str
    parent_span_id: str = ""
    service_id:     str
    operation_name: str
    start_time:     datetime
    end_time:       datetime
    duration_ms:    float = 0.0
    status_code:    str = "OK"         # OK / ERROR / UNSET
    attributes:     dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.duration_ms == 0.0 and self.end_time > self.start_time:
            object.__setattr__(
                self,
                "duration_ms",
                (self.end_time - self.start_time).total_seconds() * 1000,
            )


class NormalizedTrace(BaseModel):
    """A complete trace = collection of spans."""
    trace_id:  str
    service_id: str          # root span's service
    spans:     list[NormalizedSpan]

    def to_kafka_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


# ─── Webhook models ───────────────────────────────────────────────────────────

class VercelLogEntry(BaseModel):
    """Shape of a single entry in a Vercel Log Drain payload."""
    id:          str = ""
    message:     str
    timestamp:   int     # Unix ms
    source:      str = "build"
    projectId:   str = ""
    deploymentId: str = ""
    level:       str = "info"

    def to_normalized_log(self, service_id: str) -> NormalizedLog:
        return NormalizedLog(
            service_id=service_id,
            level=self.level,
            body=self.message,
            timestamp=datetime.fromtimestamp(self.timestamp / 1000, tz=timezone.utc),
            attributes={"source": self.source, "deployment_id": self.deploymentId},
        )


class RenderLogEntry(BaseModel):
    """Shape of a Render log stream entry."""
    id:        str = ""
    timestamp: str      # ISO string
    message:   str
    level:     str = "info"
    serviceId: str = ""

    def to_normalized_log(self, service_id: str) -> NormalizedLog:
        return NormalizedLog(
            service_id=service_id or self.serviceId,
            level=self.level,
            body=self.message,
            timestamp=datetime.fromisoformat(self.timestamp.replace("Z", "+00:00")),
            attributes={"render_service_id": self.serviceId},
        )
