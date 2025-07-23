=from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import os
from ai import get_llm_reply, generate_tts  # you will create these
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

AUDIO_OUTPUT_DIR = "audio_files"
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    message: str
    personality: Optional[str] = "Base"

class ChatResponse(BaseModel):
    reply: str
    audio_url: Optional[str] = None

@app.post("/api/process_audio", response_model=ChatResponse)
async def process_audio(req: ChatRequest):
    try:
        reply_text = get_llm_reply(req.message, personality=req.personality)
        # Generate TTS and save file (filename based on a hash or uuid, for simplicity use "output.mp3")
        audio_filename = generate_tts(reply_text, AUDIO_OUTPUT_DIR)
        audio_url = f"/audio/{audio_filename}"
        return ChatResponse(reply=reply_text, audio_url=audio_url)
    except Exception as e:
        return JSONResponse(content={"reply": "", "audio_url": None, "error": str(e)}, status_code=500)

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    filepath = os.path.join(AUDIO_OUTPUT_DIR, filename)
    if not os.path.isfile(filepath):
        return JSONResponse(content={"error": "File not found"}, status_code=404)
    return FileResponse(filepath, media_type="audio/mpeg")
