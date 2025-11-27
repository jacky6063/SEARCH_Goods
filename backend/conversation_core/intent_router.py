from __future__ import annotations

from typing import Dict, Iterable, Optional, Type

from .handler_base import ConversationHandler
from .models import ConversationContext, IntentDecision


class IntentRouter:
    """Resolve intents to the proper handler implementations."""

    def __init__(self) -> None:
        self._handlers: Dict[str, ConversationHandler] = {}
        self._fallback_handler: Optional[ConversationHandler] = None

    def register(self, intent_type: str, handler: ConversationHandler) -> None:
        intent_key = intent_type.strip().lower()
        self._handlers[intent_key] = handler

    def register_many(self, mapping: Dict[str, ConversationHandler]) -> None:
        for key, handler in mapping.items():
            self.register(key, handler)

    def registered_handlers(self) -> Iterable[str]:
        return self._handlers.keys()

    def set_fallback(self, handler: ConversationHandler) -> None:
        self._fallback_handler = handler

    def resolve(self, intent: IntentDecision, ctx: ConversationContext) -> Optional[ConversationHandler]:
        if not intent.intent_type:
            return self._fallback_handler
        handler = self._handlers.get(intent.intent_type.lower())
        if handler and handler.can_handle(intent, ctx):
            return handler
        if self._fallback_handler and self._fallback_handler.can_handle(intent, ctx):
            return self._fallback_handler
        return handler
