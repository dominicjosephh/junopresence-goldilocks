# main.py
import os
from dotenv import load_dotenv
load_dotenv()  # pull in your .env variables

import openai
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

# Load API keys from env
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

app = FastAPI()

def run_whisper_transcription(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        resp = openai.Audio.transcribe("whisper-1", audio_file)
    return resp["text"].strip()

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = File(...),
    ritual_mode: Optional[str] = Form(None)
):
    # If a ritual mode is requested, serve that file instead
    if ritual_mode:
        ritual_file = f"rituals/Juno_{ritual_mode.capitalize()}_Mode.m4a"
        if os.path.exists(ritual_file):
            return JSONResponse(
                status_code=200,
                content={"ritual_mode": ritual_mode, "file": ritual_file}
            )
        return JSONResponse(status_code=404, content={"error": "Ritual not found"})

    # Otherwise, save the upload and transcribe
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, audio.filename)
    with open(file_path, "wb") as f:
        f.write(await audio.read())

    try:
        transcript = run_whisper_transcription(file_path)
    except Exception as e:
        os.remove(file_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Transcription failed: {e}"}
        )

    os.remove(file_path)
    return JSONResponse(status_code=200, content={"transcript": transcript})
