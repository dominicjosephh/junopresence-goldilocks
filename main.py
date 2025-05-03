# main.py
import os
import io
from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

import openai
import requests
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional

# Load API keys from env
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

app = FastAPI()

def run_whisper_transcription(file_path: str) -> str:
    with open(file_path, "rb") as f:
        resp = openai.Audio.transcribe("whisper-1", f)
    return resp["text"].strip()

def run_elevenlabs_tts(text: str) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.content

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = File(...),
    ritual_mode: Optional[str] = Form(None)
):
    if ritual_mode:
        ritual_file = f"rituals/Juno_{ritual_mode.capitalize()}_Mode.m4a"
        if os.path.exists(ritual_file):
            return JSONResponse(status_code=200, content={"ritual_mode": ritual_mode, "file": ritual_file})
        return JSONResponse(status_code=404, content={"error": "Ritual not found"})
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, audio.filename)
    with open(file_path, "wb") as f:
        f.write(await audio.read())
    try:
        transcript = run_whisper_transcription(file_path)
    except Exception as e:
        os.remove(file_path)
        return JSONResponse(status_code=500, content={"error": f"Transcription failed: {e}"})
    os.remove(file_path)
    return JSONResponse(status_code=200, content={"transcript": transcript})

@app.post("/api/tts")
async def tts_endpoint(text: str = Form(...)):
    try:
        audio_bytes = run_elevenlabs_tts(text)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"TTS failed: {e}"})
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
