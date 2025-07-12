import os
import json
import random
import hashlib
import time
import threading
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv

# --------- Import Phase 2 Modules ---------
from emotion_intelligence import voice_emotion_analyzer, emotional_adapter
from redis_setup import cache_manager, performance_monitor, init_redis, redis_client
from redis_integration import (
    get_smart_ai_reply_cached, 
    get_enhanced_memory_context_cached,
    generate_tts_cached,
    spotify_search_with_cache,
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
    # You can import your benchmark_performance function here or implement it modularly
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5020)
