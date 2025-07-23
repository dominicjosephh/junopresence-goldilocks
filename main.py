from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import Optional
from utils import get_together_ai_reply
import uvicorn

app = FastAPI()

# ---- CORS Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- AudioRequest Model ----
class AudioRequest(BaseModel):
    messages: list
    personality: str = "Base"
    audio_url: Optional[str] = None
    music_command: Optional[str] = None

# ---- Startup Event ----
@app.on_event("startup")
async def startup_event():
    print("✅ Starting Juno Presence AI Backend...")
    print("🎭 Voice Mode: Base")
    print("📦 All modules loaded successfully")

# ---- Process Audio Endpoint ----
@app.post("/api/process_audio")
async def process_audio(request: AudioRequest):
    try:
        print(f"Incoming request with personality: {request.personality}")
        print(f"Incoming messages: {request.messages}")

        # Robust input validation + always call LLM for debug!
        if not isinstance(request.messages, list) or not request.messages:
            print("⚠️ messages missing or empty! Using fallback.")
            messages = [{"role": "user", "content": "Say something witty!"}]
        else:
            messages = request.messages

        last_msg = messages[-1]
        if not isinstance(last_msg, dict) or "content" not in last_msg or not last_msg["content"]:
            print("⚠️ Last message invalid, adding fallback content.")
            messages[-1] = {"role": "user", "content": "Say something clever!"}

        print("🟩 About to call get_together_ai_reply() with:", messages)
        reply = get_together_ai_reply(
            messages=messages,
            personality=request.personality,
            max_tokens=150
        )
        print("🟦 LLM reply:", reply)

        return {
            "reply": reply if isinstance(reply, str) and reply else "",
            "error": None,
            "audio_url": getattr(request, "audio_url", None),
            "music_command": getattr(request, "music_command", None),
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
        print(f"🔥 Unexpected error in process_audio: {e}")
        return {
            "reply": "Sorry, something went wrong on the server.",
            "error": str(e),
            "audio_url": getattr(request, "audio_url", None),
            "music_command": getattr(request, "music_command", None),
            "truncated": 0
        }

# ---- (Optional) Uvicorn Entry ----
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5020)
