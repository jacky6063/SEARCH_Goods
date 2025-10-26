from __future__ import annotations
import asyncio
from typing import Any, Awaitable, Callable, Optional

DEFAULT_TIMEOUT = 20  # 秒

async def safe_awaitable(
    coro: Awaitable[Any],
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[Any]:
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except Exception:
        return None

async def safe_call_async(
    fn: Callable[..., Awaitable[Any]],
    *args: Any,
    timeout: float = DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> Optional[Any]:
    try:
        return await asyncio.wait_for(fn(*args, **kwargs), timeout=timeout)
    except Exception:
        return None

def safe_call_sync(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Optional[Any]:
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None