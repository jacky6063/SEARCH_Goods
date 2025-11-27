from __future__ import annotations

import asyncio
import logging
from llm_service import _get_client, OPENAI_MODEL

_logger = logging.getLogger(__name__)

_SYSTEM_MESSAGE = "You are the SEARCH_Goods content engine. Follow every instruction carefully."


def get_openai_client():
    """Expose cached OpenAI client for other modules."""
    return _get_client()


async def call_openai(prompt: str, *, temperature: float = 0.45, max_tokens: int = 800) -> str:
    """
    非同步呼叫 OpenAI，回傳模型輸出文字。
    若缺少 API key 或發生錯誤，回傳空字串避免整體流程失敗。
    """
    prompt = (prompt or "").strip()
    if not prompt:
        return ""

    client = _get_client()
    if not client:
        _logger.warning("Content engine skipped because OpenAI client is unavailable")
        return ""

    def _call() -> str:
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": _SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt},
                ],
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            _logger.error("Content engine call failed: %s", exc)
            return ""

    return await asyncio.to_thread(_call)
