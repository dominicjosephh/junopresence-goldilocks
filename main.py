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

openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

app = FastAPI()


def run_whisper_transcription(fp: str) -> str:
    with open(fp, "rb") as f:
        resp = openai.Audio.transcribe("whisper-1", f)
    return resp["text"].strip()


def run_chatgpt_response(text: str) -> str:
    comp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are Juno, a witty, caring companion."},
            {"role": "user",   "content": text}
        ]
    )
    return comp.choices[0].message.content.strip()


def run_elevenlabs_tts(text: str) -> bytes:
    if not (ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID):
        raise ValueError("Missing ElevenLabs API key or voice ID")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept":        "audio/mpeg",
        "Content-Type":  "application/json",
        "xi-api-key":    ELEVENLABS_API_KEY
    }
    payload = {"text": text, "voice_settings": {"stability":0.5,"similarity_boost":0.75}}
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    return r.content


@app.post("/api/process_audio")
async def process_audio(
    audio: Optional[UploadFile] = File(None),
    ritual_mode: Optional[str] = Form(None)
):
    # Ritual shortcut
    if ritual_mode:
        path = f"rituals/Juno_{ritual_mode}.m4a"
        if os.path.exists(path):
            return JSONResponse(content={"ritual_mode": ritual_mode, "file": path}, status_code=200)
        return JSONResponse(content={"error":"Ritual not found"}, status_code=404)

    # Must supply audio
    if audio is None:
        return JSONResponse(content={"error":"No audio provided"}, status_code=400)

    # Save to temp
    tmp = "temp"
    os.makedirs(tmp, exist_ok=True)
    fp = os.path.join(tmp, audio.filename)
    with open(fp, "wb") as f:
        f.write(await audio.read())

    # Run pipeline
    try:
        text      = run_whisper_transcription(fp)
        reply     = run_chatgpt_response(text)
        tts_bytes = run_elevenlabs_tts(reply)
    except Exception as e:
        os.remove(fp)
        return JSONResponse(content={"error":f"Processing failed: {e}"}, status_code=500)

    os.remove(fp)
    b64 = base64.b64encode(tts_bytes).decode()

    return JSONResponse(
        content={"transcript": text, "reply": reply, "tts": b64},
        status_code=200
     )
