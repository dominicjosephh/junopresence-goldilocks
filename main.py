from fastapi import FastAPI, WebSocket, Request, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ai import generate_reply, get_models, set_personality, get_personality
from memory import (
    store_memory, retrieve_memory, get_memory_summary, get_recent_conversations,
    get_personal_facts, get_favorite_topics, get_relationships
)
from music import (
    handle_music_command, create_playlist, get_music_recommendations,
    get_music_insights, log_current_track
)
from speech import transcribe_audio
from tts import synthesize_speech

# TODO: Import any additional modules as you refactor code out of backend.py

app = FastAPI(title="Juno Presence AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for prod!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- AI Endpoints ----
@app.post("/api/v1/ai/chat")
async def ai_chat_endpoint(user_input: str = Form(...), chat_history: str = Form(""), personality: str = Form("Base")):
    reply = generate_reply(user_input, chat_history, personality)
    return {"reply": reply}

@app.get("/api/v1/ai/models")
async def ai_models():
    return {"models": get_models()}

@app.get("/api/v1/ai/personality")
async def get_ai_personality():
    return {"personality": get_personality()}

@app.put("/api/v1/ai/personality")
async def set_ai_personality_endpoint(personality: str):
    set_personality(personality)
    return {"status": "ok"}

# ---- Voice Endpoints ----
@app.websocket("/api/v1/voice/convo")
async def websocket_convo(websocket: WebSocket):
    await websocket.accept()
    while True:
        audio_bytes = await websocket.receive_bytes()
        user_text = transcribe_audio(audio_bytes)
        # TODO: add chat history/personality support
        reply = generate_reply(user_text, "", "Base")
        tts_audio = synthesize_speech(reply)
        await websocket.send_bytes(tts_audio)

@app.post("/api/v1/voice/process")
async def process_voice(audio: UploadFile):
    audio_bytes = await audio.read()
    user_text = transcribe_audio(audio_bytes)
    return {"text": user_text}

# ---- Memory Endpoints ----
@app.post("/api/v1/memory/store")
async def memory_store(key: str, value: str):
    store_memory(key, value)
    return {"status": "ok"}

@app.get("/api/v1/memory/summary")
async def memory_summary():
    return get_memory_summary()

@app.get("/api/v1/memory/conversations")
async def memory_conversations(limit: int = 10):
    return get_recent_conversations(limit)

@app.get("/api/v1/memory/facts")
async def memory_facts():
    return get_personal_facts()

@app.get("/api/v1/memory/topics")
async def memory_topics():
    return get_favorite_topics()

@app.get("/api/v1/memory/relationships")
async def memory_relationships():
    return get_relationships()

# ---- Music Endpoints ----
@app.post("/api/v1/music/command")
async def music_command(command: str, spotify_token: str = Form("")):
    return handle_music_command(command, spotify_token)

@app.post("/api/v1/music/playlist")
async def music_playlist(playlist_name: str, context: str, spotify_token: str = Form("")):
    return create_playlist(playlist_name, context, spotify_token)

@app.get("/api/v1/music/recommendations")
async def music_recommendations(context: str, spotify_token: str = ""):
    return get_music_recommendations(context, spotify_token=spotify_token)

@app.get("/api/v1/music/insights")
async def music_insights():
    return get_music_insights()

@app.post("/api/v1/music/log_track")
async def log_track(spotify_token: str = Form(""), context: str = Form("general")):
    log_current_track(spotify_token, context)
    return {"status": "ok"}

# ---- Health/Utility ----
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
