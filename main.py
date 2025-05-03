# main.py
import os
import openai
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

# Make sure you have OPENAI_API_KEY in your environment
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    # Ritual handling (unchanged)
    if ritual_mode:
        ritual_file = f"rituals/Juno_{ritual_mode.capitalize()}_Mode.m4a"
        if os.path.exists(ritual_file):
            return JSONResponse(
                status_code=200,
                content={"ritual_mode": ritual_mode, "file": ritual_file}
            )
        return JSONResponse(status_code=404, content={"error": "Ritual not found"})

    # Save upload to temp
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, audio.filename)
    with open(file_path, "wb") as f:
        f.write(await audio.read())

    # Transcribe
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
