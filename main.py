from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from utils import get_together_ai_reply
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AudioRequest(BaseModel):
    messages: list
    personality: str = "Base"
    audio_url: str = None
    music_command: str = None

@app.on_event("startup")
async def startup_event():
    print("✅ Starting Juno Presence AI Backend...")
    print("🎯 Voice Mode: Base")
    print("🔁 All modules loaded successfully")

@app.post("/api/process_audio")
async def process_audio(request: AudioRequest):
    try:
        print(f"Incoming request with personality: {request.personality}")
        print(f"Incoming messages: {request.messages}")

        # Robust input validation
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

    except (ValidationError, ValueError) as e:
        print(f"❌ Validation error in process_audio: {e}")
        return {
            "reply": "Sorry, I encountered a validation error.",
            "error": str(e),
            "audio_url": getattr(request, "audio_url", None),
            "music_command": getattr(request, "music_command", None),
            "truncated": 0
        }
    except Exception as e:
        print(f"❌ General error in process_audio: {e}")
        return {
            "reply": "Sorry, I encountered an error.",
            "error": str(e),
            "audio_url": getattr(request, "audio_url", None),
            "music_command": getattr(request, "music_command", None),
            "truncated": 0
        }

@app.get("/healthcheck")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5020, reload=True)
