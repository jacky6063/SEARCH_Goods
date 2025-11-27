"""Centralized Supabase client helpers for SEARCH_Goods backend."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client


class SupabaseConfigError(RuntimeError):
    """Raised when required Supabase environment variables are missing."""


_dotenv_loaded = False


def _ensure_env_loaded() -> None:
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_dotenv(override=False)
        _dotenv_loaded = True


def _get_env(name: str, *, required: bool = True) -> Optional[str]:
    value = os.getenv(name)
    if value:
        return value.strip()
    if required:
        raise SupabaseConfigError(f"Environment variable '{name}' is required for Supabase access.")
    return None


def _resolve_credentials(*, prefer_service_role: bool) -> tuple[str, str]:
    _ensure_env_loaded()
    url = _get_env("SUPABASE_URL")
    key: Optional[str] = None
    if prefer_service_role:
        key = _get_env("SUPABASE_SERVICE_KEY", required=False)
    if not key:
        key = _get_env("SUPABASE_KEY")
    return url, key


@lru_cache(maxsize=1)
def get_supabase_client(*, prefer_service_role: bool = False) -> Client:
    """
    Return a cached Supabase client.

    Args:
        prefer_service_role: When True, attempt to use `SUPABASE_SERVICE_KEY`
            (falls back to `SUPABASE_KEY` if unset). Use this for server-side
            writes that bypass RLS; keep False for anon-key read paths.
    """
    url, key = _resolve_credentials(prefer_service_role=prefer_service_role)
    return create_client(url, key)


__all__ = [
    "SupabaseConfigError",
    "get_supabase_client",
]
