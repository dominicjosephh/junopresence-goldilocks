import os
import json
import random
import hashlib
import time
import threading
from fastapi import FastAPI, UploadFile, Form, Request, File, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv
import cv2
import numpy as np
import uuid

# --------- Import Phase 2 Modules ---------
from emotion_intelligence import voice_emotion_analyzer, emotional_adapter
from redis_setup import cache_manager, performance_monitor, init_redis, redis_client
from redis_integration import (
    get_smart_ai_reply_cached, 
    get_enhanced_memory_context_cached,
    generate_tts_cached,
)
from process_audio import process_audio_enhanced
# Import other modules as needed (music intelligence, etc)

# --------- Environment setup ---------
load_dotenv()
AUDIO_DIR = "static"
AUDIO_FILENAME = "juno_response.mp3"
AUDIO_PATH = os.path.join(AUDIO_DIR, AUDIO_FILENAME)
os.makedirs(AUDIO_DIR, exist_ok=True)

# --------- FastAPI App ---------
app = FastAPI()
app.mount("/static", StaticFiles(directory=AUDIO_DIR), name="static")

# --------- WebSocket Session State ---------
sessions = {}

# --------- Speech-to-Text (Whisper) Integration Stub ---------
# If you have a speech_service.py module, import and use it instead!
def transcribe_audio(audio_bytes) -> str:
    """
    Replace this stub with your actual Whisper speech-to-text logic.
    For example, you might use speech_service.get_speech_service().transcribe_audio(audio_bytes)
    """
    # Example using a hypothetical speech_service:
    # speech_service = get_speech_service(model_size="base")
    # result = speech_service.transcribe_audio(audio_bytes)
    # return result["text"]
    return "Transcribed text goes here."  # Stub for testing

# --------- WebSocket Convo Mode ---------
@app.websocket("/ws/convo")
async def websocket_convo(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"history": [], "voice_mode": "Base"}
    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            # STEP 1: Transcribe audio chunk to text (Whisper STT)
            user_text = transcribe_audio(audio_chunk)
            sessions[session_id]["history"].append({"role": "user", "content": user_text})
            # STEP 2: Generate reply (LLM - to be implemented in next step)
            # reply = generate_reply(sessions[session_id]["history"], sessions[session_id]["voice_mode"])
            # sessions[session_id]["history"].append({"role": "assistant", "content": reply})
            # STEP 3: Synthesize reply to audio (TTS - to be implemented in later step)
            # reply_audio = synthesize_tts(reply, sessions[session_id]["voice_mode"])
            # await websocket.send_bytes(reply_audio)
            # For now, send transcript text back for testing
            await websocket.send_text(user_text)
    except WebSocketDisconnect:
        sessions.pop(session_id, None)

# --------- Startup Event ---------
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting ENHANCED Juno backend with Redis caching + Emotional Intelligence...")
    # Initialize Redis
    redis_available = init_redis()
    if redis_available:
        print("🔥 Redis caching system enabled!")
    else:
        print("🟡 Continuing with local caching fallback")
    # Record system metrics on startup
    performance_monitor.record_system_metrics()
    print("✅ Backend optimization complete!")

# --------- API Endpoints ---------
# Health check
@app.get("/api/test")
async def test():
    return JSONResponse(content={"message": "ENHANCED backend with Redis, Emotional Intelligence, and performance monitoring is live!"})

# Benchmark
@app.post("/api/benchmark")
async def benchmark():
    from phase2_testing import benchmark_performance
    results = benchmark_performance()
    return JSONResponse(content=results)

# Cache stats
@app.get("/api/cache/stats")
async def get_cache_stats():
    from redis_integration import get_cache_stats
    return await get_cache_stats()

# Clear cache
@app.post("/api/cache/clear")
async def clear_cache_endpoint():
    from redis_integration import clear_cache_endpoint
    return await clear_cache_endpoint()

# Performance metrics
@app.get("/api/performance")
async def get_performance_metrics():
    from redis_integration import get_performance_metrics
    return await get_performance_metrics()

# Emotion analysis endpoints
from emotion_intelligence import get_emotion_analysis, get_emotion_history, test_emotion_analysis
app.get("/api/emotion/analysis")(get_emotion_analysis)
app.get("/api/emotion/history")(get_emotion_history)
app.post("/api/emotion/test")(test_emotion_analysis)

# --------- Enhanced process_audio endpoint ---------
app.post("/api/process_audio")(process_audio_enhanced)

# --------- Exception Handler ---------
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    print(f"❌ [Universal Exception] {exc}")
    return JSONResponse(
        status_code=500,
        content={"reply": None, "audio_url": None, "error": f"Server error: {str(exc)}"}
    )

# --------- Agentic AI Endpoints ---------
from pydantic import BaseModel

class TaskRequest(BaseModel):
    command: str

class ScheduleRequest(BaseModel):
    message: str
    delay_seconds: int

def agent_command(command: str):
    if command.lower() == "hello":
        return {"result": "Hello from Juno!"}
    elif command.lower() == "time":
        return {"result": f"Current time is {time.strftime('%H:%M:%S')}"}
    elif command.lower() == "weather":
        return {"result": "It's sunny outside!"}
    else:
        return {"result": f"Unknown command: {command}"}

def schedule_message(message: str, delay: int):
    def delayed():
        time.sleep(delay)
        print(f"[Scheduled] {message}")
    threading.Thread(target=delayed).start()

@app.post("/agent/task")
async def run_agent_task(request: TaskRequest):
    output = agent_command(request.command)
    return JSONResponse(content=output)

@app.post("/agent/schedule")
async def schedule_agent_task(request: ScheduleRequest):
    schedule_message(request.message, request.delay_seconds)
    return JSONResponse(content={"result": f"Scheduled message '{request.message}' in {request.delay_seconds} seconds."})

# --------- Computer Vision Endpoint ---------
@app.post("/vision/analyze")
async def analyze_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")
        faces = face_cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5)
        result = {"faces_detected": len(faces), "smiles_detected": 0}
        smiles_total = 0
        for (x, y, w, h) in faces:
            roi = img[y:y+h, x:x+w]
            smiles = smile_cascade.detectMultiScale(roi, scaleFactor=1.7, minNeighbors=22)
            smiles_total += len(smiles)
        result["smiles_detected"] = smiles_total
        return JSONResponse(content=result)
    except Exception as e:
        print(f"[Vision Error] {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --------- Predictive Intelligence: Scheduled Reminders Suggestion ---------
reminder_history = {}

def update_reminder_history(user_id: str):
    if user_id not in reminder_history:
        reminder_history[user_id] = 1
    else:
        reminder_history[user_id] += 1
    return reminder_history[user_id]

@app.post("/predict/reminder")
async def predict_reminder(user_id: str = Form(...)):
    count = update_reminder_history(user_id)
    if count >= 3:
        suggestion = "You schedule reminders often. Would you like to automate a recurring reminder?"
    else:
        suggestion = "No suggestion yet. Keep scheduling reminders!"
    return JSONResponse(content={"user_id": user_id, "reminder_count": count, "suggestion": suggestion})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5020)
