from app.utils.rate_limiter import RateLimiter
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
import logging

from app.chatbot.ai_engine import get_ai_reply

logger        = logging.getLogger("portfolio.chatbot")
router        = APIRouter(tags=["chatbot"])
_chat_limiter = RateLimiter.for_chat()   # strict — instantiated once


class ChatRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 1000:
            raise ValueError("Message too long — maximum 1000 characters")
        return v


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    request: Request,
    limiter: RateLimiter = Depends(lambda: _chat_limiter),  # injected
):
    ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
         or (request.client.host if request.client else "unknown")

    if not limiter.is_allowed(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many messages. Please wait a moment before sending again."
        )

    try:
        reply = await get_ai_reply(req.message)
        return ChatResponse(reply=reply)
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate reply")