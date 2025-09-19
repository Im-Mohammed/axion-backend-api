# chatbot/router.py

from fastapi import APIRouter
from pydantic import BaseModel
from chatbot.ai_engine import get_ai_reply

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat_endpoint(req: ChatRequest):
    reply = get_ai_reply(req.message)
    return {"reply": reply}
