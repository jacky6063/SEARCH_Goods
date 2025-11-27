"""
Simplified voice helpers used by the new Whisper-only implementation.

The previous version tried to support multiple STT vendors and bundled a large
set of UI helpers in the same module.  The refreshed design keeps the scope
tight:

* Only OpenAI Whisper is supported for speech-to-text.
* Voice replies are generated for two intents: goods search & company profile.
* The helper returns consistent directives so the frontend knows when to keep
  listening or close the voice session.
"""
from __future__ import annotations

import io
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from services.llm_client import get_openai_client

VOICE_ALLOWED_INTENTS: Sequence[str] = ("goods_search", "company_profile")
VOICE_REJECT_MESSAGE = "目前語音模式僅支援商品或公司資料查詢，已為您關閉語音模式，請改用文字輸入。"
GOODS_NAME_FIELDS = ("商品名稱", "name", "title")
GOODS_PRICE_FIELDS = ("售價", "price", "Price", "價格")
COMPANY_NAME_FIELDS = ("公司名稱", "brand", "name", "CompanyName")
COMPANY_CONTACT_FIELDS = ("phone", "電話", "連絡電話", "聯絡電話")


class VoiceServiceError(Exception):
    """Raised when speech-to-text fails or cannot be executed."""


def is_intent_allowed(intent: str | None) -> bool:
    """Whitelisted intents for voice mode."""
    if not intent:
        return False
    return intent.strip() in VOICE_ALLOWED_INTENTS


def build_intent_reject_payload() -> Dict[str, Any]:
    """Return a directive that closes the voice session immediately."""
    return {
        "reply": VOICE_REJECT_MESSAGE,
        "voice_summary": VOICE_REJECT_MESSAGE,
        "voice_mode_active": False,
        "voice_session_end": True,
    }


def _first_non_empty(record: Mapping[str, Any], fields: Iterable[str]) -> str:
    for field in fields:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return ""


def summarize_goods(results: Sequence[Mapping[str, Any]], total_count: int = 0) -> str:
    if not results:
        return "暫時找不到符合條件的商品，您可以補充品牌、預算或改用文字輸入。"
    total = total_count or len(results)
    head = results[0] or {}
    name = _first_non_empty(head, GOODS_NAME_FIELDS)
    price = _first_non_empty(head, GOODS_PRICE_FIELDS)
    summary = [f"為您找到 {total} 件相關商品"]
    if name:
        summary.append(f"，包含「{name}」")
    if price:
        summary.append(f"，價格約 {price}")
    if total > len(results):
        summary.append(f"，另外還有 {total - len(results)} 款可選")
    summary.append("。")
    return "".join(summary)


def summarize_company(results: Sequence[Mapping[str, Any]]) -> str:
    if not results:
        return "暫時沒有查到相關公司資訊，請再提供公司全名或其他線索。"
    head = results[0] or {}
    name = _first_non_empty(head, COMPANY_NAME_FIELDS) or "該公司"
    phone = _first_non_empty(head, COMPANY_CONTACT_FIELDS)
    summary = [f"{name}的主要資訊已為您整理完成"]
    if phone:
        summary.append(f"，聯絡電話為 {phone}")
    summary.append("，您可以點擊卡片查看更多細節。")
    return "".join(summary)


def build_voice_summary(
    results: Sequence[Mapping[str, Any]],
    query_type: str,
    total_count: int = 0,
) -> str:
    if query_type == "company_profile":
        return summarize_company(results)
    return summarize_goods(results, total_count)


def build_voice_directives(
    results: Sequence[Mapping[str, Any]],
    query_type: str,
    total_count: int = 0,
) -> Dict[str, Any]:
    summary = build_voice_summary(results, query_type, total_count)
    has_results = bool(results)
    return {
        "voice_summary": summary,
        # 有結果時就朗讀後結束語音；無結果則保持開啟讓使用者立即補充
        "voice_mode_active": not has_results,
        "voice_session_end": has_results,
    }


def _get_openai_client() -> Any:
    client = get_openai_client()
    if not client:
        raise VoiceServiceError("OpenAI 客戶端不可用，請確認 OPENAI_API_KEY。")
    return client


async def transcribe_audio(
    audio_data: bytes,
    *,
    language: str = "zh-TW",
    model: str = "whisper-1",
) -> Dict[str, Any]:
    """Run Whisper transcription for the provided audio bytes."""
    if not audio_data:
        raise VoiceServiceError("音訊資料為空")

    client = _get_openai_client()
    buffer = io.BytesIO(audio_data)
    buffer.name = "voice-input.webm"
    lang_code = (language or "zh-TW").split("-")[0]
    try:
        response = client.audio.transcriptions.create(
            model=model or "whisper-1",
            file=buffer,
            language=lang_code,
            response_format="verbose_json",
        )
    except Exception as exc:  # pragma: no cover - exercised via mocks
        raise VoiceServiceError(f"Whisper 轉錄失敗: {exc}") from exc

    text = getattr(response, "text", None)
    if text is None and isinstance(response, Mapping):
        text = response.get("text")
    if not text:
        raise VoiceServiceError("Whisper 未回傳文字內容")

    language_code = getattr(response, "language", None)
    if language_code is None and isinstance(response, Mapping):
        language_code = response.get("language")

    return {
        "text": text.strip(),
        "language": (language_code or lang_code).lower(),
        "confidence": 1.0,  # Whisper API 不提供信心分數
    }
