"""
FaultLens Backend — Application Settings
Loaded once at startup via pydantic-settings.
All values come from environment variables or the .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # silently ignore unknown env vars
    )

    # ── Application ────────────────────────────────────────────────
    app_name: str = "FaultLens"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # ── Database (Phase 1) ─────────────────────────────────────────
    # Optional in Phase 0 — the app starts without it
    database_url: str = ""
    database_url_sync: str = ""

    # ── AI / LLM (Phase 17) ────────────────────────────────────────
    # Used by the AI explanation layer. Optional until Phase 17.
    # Get your free key at: https://console.groq.com/keys
    groq_api_key: str = ""
    # Model to use. llama-3.3-70b-versatile was shut down by Groq on 2026-08-16;
    # openai/gpt-oss-120b is Groq's recommended production replacement.
    groq_model: str = "openai/gpt-oss-120b"

    # ── Telemetry Correlation (Phase 11) ───────────────────────────
    # How many nanoseconds around a trace window to fetch correlated metrics.
    # Default: ±30 seconds expressed in nanoseconds.
    correlation_window_ns: int = 30_000_000_000

    # ── Real-time pipeline ─────────────────────────────────────────
    # Background loop: detect → incidents → RCA → AI, every N seconds.
    pipeline_auto_run: bool = True
    pipeline_interval_seconds: int = 30
    # Generate AI explanations automatically for new incidents (needs GROQ_API_KEY).
    ai_auto_explain: bool = True
    # Services that are traffic sources, not part of the system under test.
    detection_ignore_services: str = "load-generator,frontend-web"

    # ── Retention ──────────────────────────────────────────────────
    # Raw spans / metric points / logs older than this are deleted.
    # Anomalies, incidents, RCA and AI explanations are kept.
    telemetry_retention_minutes: int = 60

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
