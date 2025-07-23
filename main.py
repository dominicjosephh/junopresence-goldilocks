from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import ai  # This is your ai.py module

load_dotenv()

app = FastAPI()

# Allow all CORS origins for dev (change for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "JunoPresence Backend is running."}

@app.post("/api/process_audio")
async def process_audio(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        personality = data.get("personality", "Base")
        max_tokens = data.get("max_tokens", 150)
        # Call your LLM/AI function from ai.py
        reply = ai.get_together_ai_reply(messages, personality, max_tokens)
        return JSONResponse(content={"reply": reply, "error": None, "audio_url": None, "music_command": None, "truncated": 0})
    except Exception as e:
        return JSONResponse(content={"reply": "", "error": str(e), "audio_url": None, "music_command": None, "truncated": 0})

# Add other endpoints as needed...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5020, reload=False)
