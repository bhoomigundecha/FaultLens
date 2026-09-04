from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    # ─── Kafka / Redpanda ─────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = "localhost:19092"
    kafka_consumer_group: str = "faultlens-consumers"

    # ─── TimescaleDB ──────────────────────────────────────────────────────────
    timescale_url: str = (
        "postgresql+asyncpg://faultlens:faultlens@localhost:5432/faultlens_metrics"
    )
    timescale_sync_url: str = (
        "postgresql://faultlens:faultlens@localhost:5432/faultlens_metrics"
    )

    # ─── Elasticsearch ────────────────────────────────────────────────────────
    elasticsearch_url: str = "http://localhost:9200"
    es_logs_index: str = "faultlens-logs"
    es_incidents_index: str = "faultlens-incidents"

    # ─── Neo4j ────────────────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "faultlens123"

    # ─── PostgreSQL (incidents + agent state) ─────────────────────────────────
    postgres_url: str = (
        "postgresql+asyncpg://faultlens:faultlens@localhost:5433/faultlens"
    )
    postgres_sync_url: str = (
        "postgresql://faultlens:faultlens@localhost:5433/faultlens"
    )

    # ─── LLM Provider (Groq / Ollama) ─────────────────────────────────────────
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # ─── Ollama ───────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_timeout: int = 120

    # ─── Anomaly Detection ────────────────────────────────────────────────────
    zscore_threshold: float = 3.0
    isolation_forest_contamination: float = 0.1
    metric_window_minutes: int = 15
    # Minimum data points before running Isolation Forest
    min_isolation_forest_samples: int = 50

    # ─── Agent Worker ─────────────────────────────────────────────────────────
    agent_poll_interval_seconds: int = 30
    # How far back to look for anomaly candidates (seconds)
    anomaly_lookback_seconds: int = 120

    # ─── Ingestion ────────────────────────────────────────────────────────────
    app_host: str = "0.0.0.0"
    app_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — safe to call anywhere."""
    return Settings()
