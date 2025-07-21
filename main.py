import os
from fastapi import FastAPI, WebSocket, Request, UploadFile, Form, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from ai import generate_reply, get_models, set_personality, get_personality

# Import modular components
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

# Ensure static directory exists
os.makedirs("static", exist_ok=True)

app = FastAPI(title="Juno Presence AI Backend", version="1.0.0")

# CORS middleware for React Native
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React Native app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for audio serving
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---- BACKWARD COMPATIBILITY - Legacy Endpoint for Existing Frontend ----
@app.post("/api/process_audio")
async def process_audio_legacy(
    audio: UploadFile = File(None),
    text_input: str = Form(None),
    voice_mode: str = Form("Base"),
    chat_history: str = Form(""),
    spotify_access_token: str = Form(None),
    ritual_mode: str = Form(None),
    active_recall: str = Form("true")
):
    """Legacy endpoint for backward compatibility with existing frontend"""
    try:
        user_text = None
        
        # Handle audio input
        if audio and audio.filename:
            print(f"🎙️ Processing audio input: {audio.filename}")
            audio_bytes = await audio.read()
            print(f"📁 Audio file size: {len(audio_bytes)} bytes")
            
            if len(audio_bytes) == 0:
                return JSONResponse(content={
                    "reply": "I didn't receive any audio. Please try again!",
                    "audio_url": None,
                    "truncated": False,
                    "music_command": False,
                    "error": "Empty audio file"
                })
            
            # Transcribe audio
            user_text = transcribe_audio(audio_bytes)
            if not user_text or user_text.strip() == "":
                return JSONResponse(content={
                    "reply": "I couldn't understand what you said. Could you try speaking a bit louder?",
                    "audio_url": None,
                    "truncated": False,
                    "music_command": False,
                    "error": "No speech detected"
                })
                
        elif text_input:
            user_text = text_input.strip()
        else:
            return JSONResponse(content={
                "reply": "I didn't receive any input. Please try again!",
                "audio_url": None,
                "truncated": False,
                "music_command": False,
                "error": "No input provided"
            })

        print(f"🟢 User Input: {user_text}")
        print(f"🟢 Voice Mode: {voice_mode}")

        # Generate AI reply using new modular system
        reply = generate_reply(user_text, chat_history, voice_mode)
        
        print(f"🟢 Generated reply: {reply[:100]}...")
        
        # Generate TTS audio
        tts_audio_bytes = synthesize_speech(reply)
        
        # Save audio file for frontend to access
        audio_filename = "juno_response.mp3"
        audio_path = f"static/{audio_filename}"
        audio_url = None
        
        if tts_audio_bytes and len(tts_audio_bytes) > 0:
            try:
                with open(audio_path, "wb") as f:
                    f.write(tts_audio_bytes)
                audio_url = f"/static/{audio_filename}"
                print("✅ TTS generated successfully")
            except Exception as e:
                print(f"❌ Failed to save audio file: {e}")
        else:
            print("⚠️ No TTS audio generated")
        
        # Return in the format your frontend expects
        return JSONResponse(content={
            "reply": reply,
            "audio_url": audio_url,
            "truncated": False,
            "music_command": False,
            "error": None
        })
        
    except Exception as e:
        print(f"❌ Legacy endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "reply": f"Sorry, I encountered an error: {str(e)}",
                "audio_url": None,
                "truncated": False,
                "music_command": False,
                "error": str(e)
            }
        )

# ---- Legacy Test Endpoint ----
@app.get("/api/test")
async def test_legacy():
    return JSONResponse(content={
        "message": "Juno backend with modular architecture is live!",
        "status": "ok",
        "version": "modular-v1.0"
    })

# ---- Health Check ----
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Juno AI Backend is healthy"}

# ---- NEW MODULAR API ENDPOINTS ----

# Pydantic models for new endpoints
class ChatRequest(BaseModel):
    user_input: str
    chat_history: str = ""
    personality: str = "Base"

class MusicCommandRequest(BaseModel):
    command: str
    spotify_token: str = ""

class MusicPlaylistRequest(BaseModel):
    playlist_name: str
    context: str
    spotify_token: str = ""

class LogTrackRequest(BaseModel):
    spotify_token: str = ""
    context: str = "general"

# ---- AI Endpoints ----
@app.post("/api/v1/ai/chat")
async def ai_chat_endpoint(req: ChatRequest):
    try:
        reply = generate_reply(req.user_input, req.chat_history, req.personality)
        return {"reply": reply, "status": "success"}
    except Exception as e:
        return {"reply": f"Error: {str(e)}", "status": "error"}

@app.get("/api/v1/ai/models")
async def ai_models():
    try:
        models = get_models()
        return {"models": models, "status": "success"}
    except Exception as e:
        return {"models": [], "status": "error", "error": str(e)}

@app.get("/api/v1/ai/personality")
async def get_ai_personality():
    try:
        personality = get_personality()
        return {"personality": personality, "status": "success"}
    except Exception as e:
        return {"personality": "Base", "status": "error", "error": str(e)}

@app.put("/api/v1/ai/personality")
async def set_ai_personality_endpoint(personality: str):
    try:
        set_personality(personality)
        return {"status": "success", "message": f"Personality set to {personality}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ---- Voice Endpoints ----
@app.websocket("/api/v1/voice/convo")
async def websocket_convo(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            user_text = transcribe_audio(audio_bytes)
            reply = generate_reply(user_text, "", "Base")
            tts_audio = synthesize_speech(reply)
            await websocket.send_bytes(tts_audio)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()

@app.post("/api/v1/voice/process")
async def process_voice(audio: UploadFile):
    try:
        audio_bytes = await audio.read()
        user_text = transcribe_audio(audio_bytes)
        return {"text": user_text, "status": "success"}
    except Exception as e:
        return {"text": "", "status": "error", "error": str(e)}

# ---- Memory Endpoints ----
@app.post("/api/v1/memory/store")
async def memory_store(key: str, value: str):
    try:
        store_memory(key, value)
        return {"status": "success", "message": "Memory stored"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/v1/memory/summary")
async def memory_summary():
    try:
        summary = get_memory_summary()
        return {"summary": summary, "status": "success"}
    except Exception as e:
        return {"summary": {}, "status": "error", "error": str(e)}

@app.get("/api/v1/memory/conversations")
async def memory_conversations(limit: int = 10):
    try:
        conversations = get_recent_conversations(limit)
        return {"conversations": conversations, "status": "success"}
    except Exception as e:
        return {"conversations": [], "status": "error", "error": str(e)}

@app.get("/api/v1/memory/facts")
async def memory_facts():
    try:
        facts = get_personal_facts()
        return {"facts": facts, "status": "success"}
    except Exception as e:
        return {"facts": [], "status": "error", "error": str(e)}

@app.get("/api/v1/memory/topics")
async def memory_topics():
    try:
        topics = get_favorite_topics()
        return {"topics": topics, "status": "success"}
    except Exception as e:
        return {"topics": [], "status": "error", "error": str(e)}

@app.get("/api/v1/memory/relationships")
async def memory_relationships():
    try:
        relationships = get_relationships()
        return {"relationships": relationships, "status": "success"}
    except Exception as e:
        return {"relationships": [], "status": "error", "error": str(e)}

# ---- Music Endpoints ----
@app.post("/api/v1/music/command")
async def music_command(req: MusicCommandRequest):
    try:
        result = handle_music_command(req.command, req.spotify_token)
        return {"result": result, "status": "success"}
    except Exception as e:
        return {"result": {}, "status": "error", "error": str(e)}

@app.post("/api/v1/music/playlist")
async def music_playlist(req: MusicPlaylistRequest):
    try:
        result = create_playlist(req.playlist_name, req.context, req.spotify_token)
        return {"playlist": result, "status": "success"}
    except Exception as e:
        return {"playlist": {}, "status": "error", "error": str(e)}

@app.get("/api/v1/music/recommendations")
async def music_recommendations(context: str, spotify_token: str = ""):
    try:
        recommendations = get_music_recommendations(context, spotify_token=spotify_token)
        return {"recommendations": recommendations, "status": "success"}
    except Exception as e:
        return {"recommendations": [], "status": "error", "error": str(e)}

@app.get("/api/v1/music/insights")
async def music_insights():
    try:
        insights = get_music_insights()
        return {"insights": insights, "status": "success"}
    except Exception as e:
        return {"insights": {}, "status": "error", "error": str(e)}

@app.post("/api/v1/music/log_track")
async def log_track(req: LogTrackRequest):
    try:
        log_current_track(req.spotify_token, req.context)
        return {"status": "success", "message": "Track logged"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ---- Cache Management (for compatibility) ----
@app.post("/api/clear_cache")
async def clear_cache():
    try:
        # This would clear any caches in the AI module
        return {"status": "success", "message": "Cache cleared"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/cache_stats")
async def cache_stats():
    try:
        # Return basic cache statistics
        return {
            "status": "success",
            "cache_info": {
                "backend_type": "modular",
                "ai_module_loaded": True,
                "memory_module_loaded": True,
                "music_module_loaded": True,
                "speech_module_loaded": True,
                "tts_module_loaded": True
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ---- Error Handlers ----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Global exception: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "reply": "I encountered an unexpected error. Please try again.",
            "audio_url": None,
            "error": str(exc),
            "status": "error"
        }
    )

# ---- Startup Event ----
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Juno Presence AI Backend (Modular Architecture)")
    print("✅ All modules loaded successfully")
    print("🎯 Backend ready for frontend connections")

# ---- Main Entry Point ----
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Juno Presence AI Backend...")
    uvicorn.run(app, host="0.0.0.0", port=5020)
