"""
FaultLens Backend — Structured Application Logging

Colorized for terminal, structured for production.
Colors auto-disable when stdout is not a TTY (e.g., Docker logs, CI).
"""
import logging
import sys
from app.core.config import get_settings

# ── ANSI colors (only if the terminal supports them) ──────────────────────────
_IS_TTY = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_RESET  = "\033[0m"  if _IS_TTY else ""
_BOLD   = "\033[1m"  if _IS_TTY else ""
_DIM    = "\033[2m"  if _IS_TTY else ""
_CYAN   = "\033[36m" if _IS_TTY else ""
_GREEN  = "\033[32m" if _IS_TTY else ""
_YELLOW = "\033[33m" if _IS_TTY else ""
_RED    = "\033[31m" if _IS_TTY else ""
_BRED   = "\033[91m" if _IS_TTY else ""
_GREY   = "\033[90m" if _IS_TTY else ""

_LEVEL_STYLE = {
    "DEBUG":    (_DIM   + _GREY,   "·"),
    "INFO":     (_GREEN,            "→"),
    "WARNING":  (_YELLOW,           "⚠"),
    "ERROR":    (_RED,              "✗"),
    "CRITICAL": (_BRED  + _BOLD,   "✗✗"),
}


class _ColorFormatter(logging.Formatter):
    """
    Formatter that adds ANSI color and an emoji prefix per log level.

    Example output:
      2026-10-15T12:00:01 → INFO     app.services.anomaly  Z-score spike on payment: http.errors (Z=8.2)
      2026-10-15T12:00:02 ⚠ WARNING  app.services.rca      No RCA candidates for incident 3
      2026-10-15T12:00:03 ✗ ERROR    app.services.ai       Groq call failed: timeout
    """
    def format(self, record: logging.LogRecord) -> str:
        color, icon = _LEVEL_STYLE.get(record.levelname, ("", "•"))
        ts    = self.formatTime(record, "%Y-%m-%dT%H:%M:%S")
        level = f"{record.levelname:<8}"
        name  = record.name

        # Shorten noisy module prefixes
        name = name.replace("app.", "")

        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        return (
            f"{_GREY}{ts}{_RESET} "
            f"{color}{icon} {level}{_RESET} "
            f"{_CYAN}{name:<32}{_RESET} "
            f"{msg}"
        )


def setup_logging() -> None:
    """
    Configure application-wide structured logging.
    Call this once during app startup in main.py.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_ColorFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # ── Third-party noise control ─────────────────────────────────────────
    # SQLAlchemy: show queries only if LOG_LEVEL=DEBUG
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.log_level.upper() == "DEBUG" else logging.WARNING
    )
    # Uvicorn: always show access logs (each HTTP request)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    # Groq SDK: show only warnings
    logging.getLogger("groq").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        "FaultLens logging ready │ env=%s level=%s tty=%s",
        settings.app_env,
        settings.log_level,
        _IS_TTY,
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — use this throughout the app."""
    return logging.getLogger(name)
