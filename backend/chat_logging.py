"""Supabase logging helpers for chat sessions/messages/events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence
import logging

from supabase import Client

from supabase_client import SupabaseConfigError, get_supabase_client

logger = logging.getLogger(__name__)


class ChatLoggingError(RuntimeError):
    """Raised when Supabase logging fails."""


def _isoformat(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def _clean(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in payload.items() if v is not None}


def _client() -> Client:
    return get_supabase_client(prefer_service_role=True)


def _insert(table: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        response = _client().table(table).insert(payload).execute()
        return response.data or []
    except SupabaseConfigError:
        raise
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.exception("Supabase insert failed for %s", table)
        raise ChatLoggingError(f"Failed to insert into {table}: {exc}") from exc


def start_session(
    *,
    module_type: str,
    user_id: Optional[str] = None,
    status: str = "ongoing",
    channel: Optional[str] = None,
    context_tags: Optional[Sequence[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    company_code: Optional[str] = None,
    company_name: Optional[str] = None,
    started_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    payload = _clean(
        {
            "module_type": module_type,
            "user_id": user_id,
            "status": status,
            "channel": channel,
            "context_tags": list(context_tags or []),
            "metadata": metadata or {},
            "company_code": company_code,
            "company_name": company_name,
            "started_at": _isoformat(started_at),
        }
    )
    data = _insert("chat_sessions", payload)
    return data[0] if data else payload


def append_message(
    *,
    session_id: str,
    role: str,
    content: str,
    payload: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
    source_module: Optional[str] = None,
    state: str = "received",
) -> Dict[str, Any]:
    record = _clean(
        {
            "session_id": session_id,
            "role": role,
            "content": content,
            "payload": payload or {},
            "created_at": _isoformat(created_at),
            "source_module": source_module,
            "state": state,
        }
    )
    data = _insert("chat_messages", record)
    return data[0] if data else record


def log_recommendations(
    *,
    session_id: str,
    message_id: int,
    recommendations: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, rec in enumerate(recommendations):
        product_id = rec.get("product_id")
        product_name = rec.get("product_name")
        if not product_id or not product_name:
            logger.warning("Skip recommendation missing product info: %s", rec)
            continue
        rows.append(
            _clean(
                {
                    "session_id": session_id,
                    "message_id": message_id,
                    "product_id": product_id,
                    "product_name": product_name,
                    "source_rank": rec.get("source_rank", idx + 1),
                    "confidence": rec.get("confidence"),
                }
            )
        )

    if not rows:
        return []

    try:
        response = _client().table("product_recommendations").insert(rows).execute()
        return response.data or rows
    except SupabaseConfigError:
        raise
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.exception("Supabase insert failed for product_recommendations")
        raise ChatLoggingError(f"Failed to log recommendations: {exc}") from exc


def log_session_event(
    *,
    session_id: str,
    event_type: str,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    record = _clean(
        {
            "session_id": session_id,
            "event_type": event_type,
            "from_status": from_status,
            "to_status": to_status,
            "details": details or {},
            "created_at": _isoformat(created_at),
        }
    )
    data = _insert("session_events", record)
    return data[0] if data else record


__all__ = [
    "append_message",
    "ChatLoggingError",
    "log_recommendations",
    "log_session_event",
    "start_session",
]
