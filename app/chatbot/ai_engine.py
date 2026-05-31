"""
ai_engine.py
OpenRouter AI engine for the Axion chatbot.

Uses the same model fallback chain as the email service.
All API calls have timeouts and safe response parsing.
"""

import logging
import httpx

from app.chatbot.context import inject_portfolio_context
from app.settings.config import get_settings

logger   = logging.getLogger("portfolio.chatbot")
settings = get_settings()

# Fallback chain — tried in order until one succeeds
# Builds the priority list at startup, skips any model not set in .env
# Build priority list at startup — skip any not configured in .env
MODEL_PRIORITY = [
    m for m in [settings.model_c1, settings.model_c2, settings.model_c3]
    if m.strip()
]


_FALLBACK_REPLY = (
    "I'm having trouble connecting right now. "
    "Please try again in a moment or reach out to Mohammed directly via the contact section."
)


async def get_ai_reply(user_message: str) -> str:
    """
    Send the user message to OpenRouter and return Axion's reply.

    - Tries each model in _MODEL_PRIORITY order
    - Returns a safe fallback string if all models fail
    - Uses httpx (async) so it never blocks the FastAPI event loop
    - 20 second timeout prevents hanging requests
    """
    if not MODEL_PRIORITY:
        logger.error("No chatbot models configured — set MODEL_C1, MODEL_C2, MODEL_C3 in .env")
        return _FALLBACK_REPLY
    
    messages = inject_portfolio_context(user_message)
    headers  = {
        "Authorization": f"Bearer {settings.api.openrouter_api_key}",
        "Content-Type":  "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        
        for model in MODEL_PRIORITY:
            try:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "model":    model,
                        "messages": messages,
                    },
                )
                result = response.json()

                # Guard against malformed / empty responses
                choices = result.get("choices")
                if not choices:
                    raise ValueError(f"No choices returned from {model}")

                reply = choices[0].get("message", {}).get("content", "").strip()
                if not reply:
                    raise ValueError(f"Empty content from {model}")

                logger.info(f"Chatbot reply generated via {model}")
                return reply

            except Exception as e:
                logger.warning(f"Chatbot model {model} failed: {e}")

    logger.error("All chatbot models failed — returning fallback reply")
    return _FALLBACK_REPLY