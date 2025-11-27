from __future__ import annotations

import logging
from typing import Any, MutableMapping

_FORMAT = "%(asctime)s %(levelname)s [%(name)s] session=%(session_id)s intent=%(intent)s - %(message)s"
_CONFIGURED = False


class _ContextFilter(logging.Filter):
    """Ensure every log record has session_id/intent attributes."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        if not hasattr(record, "session_id"):
            record.session_id = "-"  # type: ignore[attr-defined]
        if not hasattr(record, "intent"):
            record.intent = "-"  # type: ignore[attr-defined]
        return True


class SafeExtraFormatter(logging.Formatter):
    """Formatter that tolerates missing extra fields.

    It ensures session_id and intent exist on the record before formatting,
    preventing "KeyError: 'session_id'" noise during early initialization
    or 3rd-party logs that don't populate these fields.
    """

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        if not hasattr(record, "session_id"):
            record.session_id = "-"  # type: ignore[attr-defined]
        if not hasattr(record, "intent"):
            record.intent = "-"  # type: ignore[attr-defined]
        return super().format(record)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that injects session/intent into extra context."""

    def process(self, msg: str, kwargs: MutableMapping[str, Any]):  # type: ignore[override]
        extra = kwargs.setdefault("extra", {})
        session_id = kwargs.pop("session_id", None)
        intent = kwargs.pop("intent", None)
        if "session_id" not in extra:
            extra["session_id"] = session_id or "-"
        if "intent" not in extra:
            extra["intent"] = intent or "-"
        return msg, kwargs


def _normalize_level(level: Any) -> int:
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)
    if isinstance(level, int):
        return level
    return logging.INFO


def configure_structured_logging(level: Any = logging.INFO) -> None:
    """Configure root logging once with shared formatter + context filter.

    - Installs a SafeExtraFormatter on all root handlers
    - Adds a context filter to backfill missing fields
    - Makes repeated calls idempotent (only level is updated)
    """
    global _CONFIGURED
    numeric_level = _normalize_level(level)
    root = logging.getLogger()
    if not _CONFIGURED:
        # Initialize with a basic handler if none exists
        logging.basicConfig(level=numeric_level)
        # Attach context filter on root
        root.addFilter(_ContextFilter())
        # Ensure all existing handlers use the safe formatter
        for h in list(root.handlers):
            try:
                h.setFormatter(SafeExtraFormatter(_FORMAT))
            except Exception:
                # Some handlers may not support custom formatters gracefully; ignore
                pass
        _CONFIGURED = True
    else:
        root.setLevel(numeric_level)
        # keep formatter/filter as-is


def get_logger(name: str) -> StructuredLoggerAdapter:
    """Return a logger adapter that automatically fills session/intent fields."""
    base = logging.getLogger(name)
    return StructuredLoggerAdapter(base, {"session_id": "-", "intent": "-"})


__all__ = [
    "configure_structured_logging",
    "get_logger",
    "StructuredLoggerAdapter",
    "SafeExtraFormatter",
]
