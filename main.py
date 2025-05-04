# main.py
import os
import io
import base64
from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

import openai
import requests
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

# Load API keys
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

app = FastAPI()

def run_whisper_transcription(file_path: str) -> str:
    with open(file_path, "rb") as f:
        resp = openai.Audio.transcribe("whisper-1", f)
    return resp["text"].strip()

def run_chatgpt_response(user_text: str) -> str:
    messages = [
        {"role": "system", "content": "You are Juno, a witty, caring companion."},
        {"role": "user", "content": user_text}
    ]
    completion = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return completion.choices[0].message.content.strip()

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
    # Ritual mode shortcut
    if ritual_mode:
        ritual_file = f"rituals/Juno_{ritual_mode.capitalize()}_Mode.m4a"
        if os.path.exists(ritual_file):
            return JSONResponse(content={"ritual_mode": ritual_mode, "file": ritual_file}, status_code=200)
        return JSONResponse(content={"error": "Ritual not found"}, status_code=404)

    # Save upload to temp
    tmp_dir = "temp"
    os.makedirs(tmp_dir, exist_ok=True)
    file_path = os.path.join(tmp_dir, audio.filename)
    with open(file_path, "wb") as f:
        f.write(await audio.read())

    try:
        transcript = run_whisper_transcription(file_path)
        reply     = run_chatgpt_response(transcript)
        tts_audio = run_elevenlabs_tts(reply)
    except Exception as e:
        os.remove(file_path)
        return JSONResponse(content={"error": f"Processing failed: {e}"}, status_code=500)

    os.remove(file_path)

    # Base64-encode the TTS bytes
    b64_str = base64.b64encode(tts_audio).decode()

    return JSONResponse(
        content={"transcript": transcript, "reply": reply, "tts": b64_str},
        status_code=200
    )
