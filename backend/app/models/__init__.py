"""app/models/__init__.py — import all ORM models so Base.metadata is populated."""
# Phase 8: telemetry tables (spans, metric_points, log_records)
from app.models.telemetry import Span, MetricPoint, LogRecord  # noqa: F401
# Phase 9: service discovery
from app.models.service import Service  # noqa: F401
# Phase 10: dependency graph
from app.models.dependency import ServiceDependency  # noqa: F401
# Phase 12: anomaly detection
from app.models.anomaly import Anomaly  # noqa: F401
# Phase 13: incident engine
from app.models.incident import Incident  # noqa: F401
# Phase 14: root cause analysis
from app.models.rca import RootCauseAnalysis  # noqa: F401
# Phase 17: AI explanation
from app.models.ai_explanation import AIExplanation  # noqa: F401

__all__ = [
    "Span", "MetricPoint", "LogRecord",
    "Service", "ServiceDependency",
    "Anomaly", "Incident", "RootCauseAnalysis", "AIExplanation",
]
