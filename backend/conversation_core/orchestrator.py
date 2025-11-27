from __future__ import annotations

from typing import Callable, Optional

from .handler_base import ConversationHandler
from .intent_router import IntentRouter
from .models import ConversationContext, ConversationInput, HandlerResult, IntentDecision

IntentDetector = Callable[[ConversationContext], IntentDecision]


class ConversationOrchestrator:
    """
    Glue layer orchestrating the chat workflow:
    1. Build context payload
    2. Run intent detection
    3. Resolve the handler via router
    4. Execute the handler and return the result
    """

    def __init__(
        self,
        intent_detector: IntentDetector,
        router: IntentRouter,
        default_handler: Optional[ConversationHandler] = None,
    ) -> None:
        self.intent_detector = intent_detector
        self.router = router
        self.default_handler = default_handler

    def handle(self, convo_input: ConversationInput) -> HandlerResult:
        ctx = ConversationContext(input=convo_input)
        intent = self.intent_detector(ctx)
        ctx.detected_intent = intent

        handler = self.router.resolve(intent, ctx)
        if not handler:
            handler = self.default_handler

        if not handler:
            raise RuntimeError(f"No handler available for intent: {intent.intent_type}")

        result = handler.handle(ctx, intent)
        if not result.ok and hasattr(handler, "fallback"):
            fallback_result = handler.fallback(ctx, intent)
            if fallback_result:
                return fallback_result

        return result
