import os
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from ai import get_together_ai_reply
import uuid

load_dotenv()

app = FastAPI()

# CORS: Allow all for development, restrict in prod!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in prod!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_OUTPUT_DIR = "audio_output"
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

@app.post("/api/process_audio")
async def process_audio(request: Request):
    """
    Handles chat and returns text + audio_url if audio was generated.
    """
    data = await request.json()
    messages = data.get("messages")
    personality = data.get("personality", "Base")
    max_tokens = data.get("max_tokens", 150)

    reply_text = get_together_ai_reply(messages, personality, max_tokens)

    # --- DUMMY AUDIO GENERATION ---
    # If you have TTS, generate audio file from reply_text here
    # For now, just fake a filename:
    audio_filename = f"{uuid.uuid4()}.wav"
    audio_path = os.path.join(AUDIO_OUTPUT_DIR, audio_filename)
    # with open(audio_path, 'wb') as f:
    #     f.write(audio_bytes)   # <-- if you had bytes

    # Return only URL to audio, NOT the bytes
    response = {
        "reply": reply_text,
        "audio_url": f"/api/audio/{audio_filename}",
        "error": None
    }
    return JSONResponse(response)

@app.get("/api/audio/{audio_filename}")
async def get_audio(audio_filename: str):
    """
    Serves audio file by filename (WAV/MP3/whatever).
    """
    audio_path = os.path.join(AUDIO_OUTPUT_DIR, audio_filename)
    if not os.path.isfile(audio_path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(audio_path, media_type="audio/wav")

@app.get("/")
def root():
    return {"status": "Juno backend running!"}
