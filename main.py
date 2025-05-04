# main.py
import os
import io
from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

import openai
import requests
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

# Load keys
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

app = FastAPI()

# Whisper transcription
def run_whisper_transcription(file_path: str) -> str:
    with open(file_path, "rb") as f:
        resp = openai.Audio.transcribe("whisper-1", f)
    return resp["text"].strip()

# ChatGPT response
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

# ElevenLabs TTS
def run_elevenlabs_tts(text: str) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    payload = {"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    resp = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.content

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = File(...),
    ritual_mode: Optional[str] = Form(None)
):
    # optional ritual
    if ritual_mode:
        file = f"rituals/Juno_{ritual_mode.capitalize()}_Mode.m4a"
        if os.path.exists(file):
            return JSONResponse(200, {"ritual_mode": ritual_mode, "file": file})
        return JSONResponse(404, {"error": "Ritual not found"})

    # save temp
    tmp = "temp"
    os.makedirs(tmp, exist_ok=True)
    path = os.path.join(tmp, audio.filename)
    with open(path, "wb") as f:
        f.write(await audio.read())

    try:
        transcript = run_whisper_transcription(path)
        reply = run_chatgpt_response(transcript)
        tts_audio = run_elevenlabs_tts(reply)
    except Exception as e:
        os.remove(path)
        return JSONResponse(500, {"error": f"Processing failed: {e}"})

    os.remove(path)

    # base64 encode audio
    b64 = io.BytesIO()
    b64.write(tts_audio)
    b64_str = base64.b64encode(b64.getvalue()).decode()

    return JSONResponse(200, {"transcript": transcript, "reply": reply, "tts": b64_str})
