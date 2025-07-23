from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
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

class AudioProcessRequest(BaseModel):
    messages: List[Dict[str, Any]] = Field(..., description="List of message objects")
    personality: str = Field("Base", description="Personality type for the AI")
    max_tokens: int = Field(150, description="Maximum number of tokens to generate")

class AudioProcessResponse(BaseModel):
    reply: str
    error: Optional[str] = None
    audio_url: Optional[str] = None  # URL to audio file, not raw bytes
    music_command: Optional[str] = None
    truncated: int = 0

@app.get("/")
async def root():
    return {"message": "JunoPresence Backend is running."}

@app.post("/api/process_audio", response_model=AudioProcessResponse)
async def process_audio(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        personality = data.get("personality", "Base")
        max_tokens = data.get("max_tokens", 150)
        
        # Call your LLM/AI function from ai.py
        reply = ai.get_together_ai_reply(messages, personality, max_tokens)
        
        # Generate audio URL if needed (implement this in your ai module)
        # audio_url = ai.generate_audio_url(reply)  # Returns URL string, not raw audio
        audio_url = None  # Currently not generating audio
        
        return AudioProcessResponse(
            reply=reply,
            error=None,
            audio_url=audio_url,  # URL to audio file, never raw binary
            music_command=None,
            truncated=0
        )
    except Exception as e:
        return AudioProcessResponse(
            reply="",
            error=str(e),
            audio_url=None,
            music_command=None,
            truncated=0
        )

# Add other endpoints as needed...

# Function to generate audio and return a URL (not the raw audio)
def generate_audio_url(text: str) -> Optional[str]:
    """
    Generate audio from text and return a URL to access it.
    Never return raw audio bytes in JSON response.
    
    Args:
        text: Text to convert to speech
        
    Returns:
        URL string to access the audio file, or None if generation failed
    """
    try:
        # Implementation would go here
        # 1. Generate audio file
        # 2. Save to disk or cloud storage
        # 3. Return URL to the file
        return None  # Placeholder
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5020, reload=False)
