# main.py
import os
from dotenv import load_dotenv
load_dotenv()  # load .env variables

import openai
import io
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

# Load OpenAI key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Transcription via Whisper API
def run_whisper_transcription(file_path: str) -> str:
    with open(file_path, "rb") as f:
        resp = openai.Audio.transcribe("whisper-1", f)
    return resp["text"].strip()

# Generate Juno's reply via ChatGPT
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

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = File(...)
):
    # Save upload to temp
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, audio.filename)
    with open(file_path, "wb") as f:
        f.write(await audio.read())

    try:
        # 1) Transcribe
        transcript = run_whisper_transcription(file_path)
        # 2) Get Juno's reply
        juno_reply = run_chatgpt_response(transcript)
    except Exception as e:
        # Cleanup and error
        os.remove(file_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Processing failed: {e}"}
        )

    # Cleanup temp file
    os.remove(file_path)

    # Return both transcript and Juno's reply
    return JSONResponse(
        status_code=200,
        content={"transcript": transcript, "reply": juno_reply}
    )
