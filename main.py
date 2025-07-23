import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from ai import get_together_ai_reply

load_dotenv()

app = FastAPI()

# Optional: update origins as needed
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AudioRequest(BaseModel):
    messages: list
    personality: str = "Base"
    audio_url: str = None
    music_command: str = None

@app.post("/api/process_audio")
async def process_audio(request: AudioRequest):
    try:
        print(f"Incoming request with personality: {request.personality}")
        print(f"Incoming messages: {request.messages}")

        # Validate messages
        if not isinstance(request.messages, list) or not request.messages:
            raise ValueError("messages must be a non-empty list")
        last_msg = request.messages[-1]
        if not isinstance(last_msg, dict) or "content" not in last_msg:
            raise ValueError("Last message must be a dict with a 'content' key")

        reply = get_together_ai_reply(
            messages=request.messages,
            personality=request.personality,
            max_tokens=150
        )

        return {
            "reply": reply if isinstance(reply, str) and reply else "",
            "error": None,
            "audio_url": request.audio_url,
            "music_command": request.music_command,
            "truncated": 0
        }
    except Exception as e:
        print(f"❌ Error in process_audio: {e}")
        return {
            "reply": "",
            "error": str(e),
            "audio_url": getattr(request, "audio_url", None),
            "music_command": getattr(request, "music_command", None),
            "truncated": 0
        }
