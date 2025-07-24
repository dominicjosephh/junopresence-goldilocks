from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from ai import get_together_ai_reply
from tts_handler import generate_tts_audio

import os

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for prod!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for TTS audio
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    personality = data.get("personality", "Base")
    reply = get_together_ai_reply(messages, personality)
    return JSONResponse(content={"reply": reply, "error": None})

@app.post("/api/tts")
async def tts_endpoint(request: Request):
    data = await request.json()
    text = data.get("text", "")
    if not text:
        return JSONResponse(content={"error": "No text provided"}, status_code=400)
    audio_url = generate_tts_audio(text)
    if not audio_url:
        return JSONResponse(content={"error": "TTS failed"}, status_code=500)
    return JSONResponse(content={"audio_url": audio_url})

@app.get("/")
async def root():
    return {"status": "ok"}
