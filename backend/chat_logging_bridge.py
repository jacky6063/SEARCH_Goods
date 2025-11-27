"""Helper utilities to bridge UI sessions with Supabase logging."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from chat_logging import (
    ChatLoggingError,
    append_message as supabase_append_message,
    log_session_event as supabase_log_session_event,
    start_session as supabase_start_session,
)
from supabase_client import SupabaseConfigError


def _isoformat(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


class ChatLoggingBridge:
    """Keeps track of UI ↔ Supabase session mapping and message logging."""

    def __init__(self, module_type: str, channel: str, logger: Optional[logging.Logger] = None) -> None:
        self.module_type = module_type
        self.channel = channel
        self.logger = logger or logging.getLogger(__name__)
        self._ui_to_supabase: Dict[str, str] = {}

    # ------------------------------------------------------------------ sessions
    def ensure_session(self, ui_session_id: Optional[str], metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if ui_session_id and ui_session_id in self._ui_to_supabase:
            return self._ui_to_supabase[ui_session_id]
        try:
            record = supabase_start_session(
                module_type=self.module_type,
                channel=self.channel,
                metadata=metadata,
            )
            supabase_session_id = record.get("session_id")
            if ui_session_id and supabase_session_id:
                self.bind_ui_session(ui_session_id, supabase_session_id)
            return supabase_session_id
        except (SupabaseConfigError, ChatLoggingError) as exc:
            self.logger.debug("Supabase start_session unavailable: %s", exc)
            return None

    def bind_ui_session(self, ui_session_id: Optional[str], supabase_session_id: Optional[str]) -> None:
        if not ui_session_id or not supabase_session_id:
            return
        first_time = ui_session_id not in self._ui_to_supabase
        self._ui_to_supabase[ui_session_id] = supabase_session_id
        if first_time:
            try:
                supabase_log_session_event(
                    session_id=supabase_session_id,
                    event_type="status_change",
                    details={"ui_session_id": ui_session_id},
                )
            except (SupabaseConfigError, ChatLoggingError) as exc:
                self.logger.debug("Skip logging session event: %s", exc)

    def get_supabase_session(self, ui_session_id: Optional[str]) -> Optional[str]:
        if not ui_session_id:
            return None
        return self._ui_to_supabase.get(ui_session_id)

    # ------------------------------------------------------------------ logging
    def log_user_message(
        self,
        ui_session_id: Optional[str],
        content: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        supabase_session_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> Optional[str]:
        supabase_session_id = supabase_session_id or self.ensure_session(ui_session_id)
        if not supabase_session_id:
            return None
        try:
            supabase_append_message(
                session_id=supabase_session_id,
                role="user",
                content=content,
                payload=payload or {},
                source_module=self.module_type,
                created_at=_isoformat(created_at),
            )
        except (SupabaseConfigError, ChatLoggingError) as exc:
            self.logger.debug("Skip supabase user log: %s", exc)
        return supabase_session_id

    def log_user_message_with_record(
        self,
        ui_session_id: Optional[str],
        content: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        supabase_session_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        與 log_user_message 類似，但回傳 Supabase 實際寫入的 message record，便於後續更新 emotion_data。
        """
        supabase_session_id = supabase_session_id or self.ensure_session(ui_session_id)
        if not supabase_session_id:
            return None, None
        record: Optional[Dict[str, Any]] = None
        try:
            record = supabase_append_message(
                session_id=supabase_session_id,
                role="user",
                content=content,
                payload=payload or {},
                source_module=self.module_type,
                created_at=_isoformat(created_at),
            )
        except (SupabaseConfigError, ChatLoggingError) as exc:
            self.logger.debug("Skip supabase user log (with record): %s", exc)
        return supabase_session_id, record

    def log_assistant_message(
        self,
        ui_session_id: Optional[str],
        reply: str,
        payload: Dict[str, Any],
        *,
        supabase_session_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        supabase_session_id = supabase_session_id or self.ensure_session(ui_session_id)
        if not supabase_session_id:
            return None
        try:
            return supabase_append_message(
                session_id=supabase_session_id,
                role="llm",
                content=reply,
                payload=self._snapshot_payload(payload),
                source_module=self.module_type,
                state="processed",
                created_at=_isoformat(created_at),
            )
        except (SupabaseConfigError, ChatLoggingError) as exc:
            self.logger.debug("Skip supabase assistant log: %s", exc)
            return None

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _snapshot_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {}
        for key in ("meta", "action", "status", "display_mode", "structured_filters"):
            if payload.get(key) is not None:
                snapshot[key] = payload.get(key)
        items = payload.get("items") or payload.get("structured_products") or []
        snapshot["items_count"] = len(items) if isinstance(items, list) else 0
        return snapshot


__all__ = ["ChatLoggingBridge"]
