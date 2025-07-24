from fastapi import APIRouter, Request
from pydantic import BaseModel
from ai import get_together_ai_reply

chat_router = APIRouter()

class ChatRequest(BaseModel):
    messages: list
    personality: str = "Base"
    audio_url: str = None
    music_command: str = None
    spotify_access_token: str = None

@chat_router.post("/api/chat")
async def chat_endpoint(body: ChatRequest, request: Request):
    reply = get_together_ai_reply(
        messages=body.messages,
        personality=body.personality
    )
    return {"reply": reply}
