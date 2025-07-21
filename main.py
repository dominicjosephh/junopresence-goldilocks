from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from ai import generate_reply, get_models, set_personality, get_personality
from pydantic import BaseModel
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
    print("✅Starting Juno Presence AI Backend...")
    print("🎯 Voice Mode: Base")
    print("🔁 All modules loaded successfully")

@app.post("/api/process_audio")
async def process_audio(request: AudioRequest):
    try:
        print(f"Incoming request with personality: {request.personality}")
        print(f"Incoming messages: {request.messages}")

        # Generate reply
        reply = generate_reply(
            messages=request.messages,
            personality=request.personality,
            max_tokens=150
        )

        print(f"🧠 Generated reply: {reply[:100]}...")  # Log a preview

        return {
            "reply": reply,
            "error": None,
            "audio_url": request.audio_url,
            "music_command": request.music_command,
            "truncated": 0
        }

    except Exception as e:
        print(f"❌ Error in process_audio: {e}")
        return {
            "reply": "Sorry, I encountered an error.",
            "error": str(e),
            "audio_url": request.audio_url,
            "music_command": request.music_command,
            "truncated": 0
        }

@app.get("/healthcheck")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5020, reload=True)
