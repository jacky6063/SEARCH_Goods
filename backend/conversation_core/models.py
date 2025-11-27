from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationInput:
    """Raw user input and environmental context received by the orchestrator."""

    user_text: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    session_id: Optional[str] = None
    locale: str = "zh-TW"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """
    Mutable context shared across detectors and handlers.

    Stores intermediate data such as intent signals, LLM responses, or backend lookups.
    """

    input: ConversationInput
    detected_intent: Optional["IntentDecision"] = None
    state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentDecision:
    """Normalized intent decision shared with the router and downstream handlers."""

    intent_type: str
    confidence: float = 0.0
    sub_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandlerResult:
    """Standardized response structure returned by handlers."""

    ok: bool
    reply: str
    payload: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    trace: Dict[str, Any] = field(default_factory=dict)
