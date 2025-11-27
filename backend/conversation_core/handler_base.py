from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import ConversationContext, HandlerResult, IntentDecision


class ConversationHandler(ABC):
    """Base class for all scenario handlers."""

    name: str = "base"

    @abstractmethod
    def can_handle(self, intent: IntentDecision, ctx: ConversationContext) -> bool:
        """Return True when the handler is willing to process the intent."""

    @abstractmethod
    def handle(self, ctx: ConversationContext, intent: IntentDecision) -> HandlerResult:
        """Execute the main business logic for the scenario."""

    def fallback(self, ctx: ConversationContext, intent: IntentDecision) -> Optional[HandlerResult]:
        """Optional fallback hook when the main handler fails."""
        return None
