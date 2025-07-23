from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os
import logging
import ai  # This is your ai.py module
from utils import safe_encode_utf8, safe_json_loads, safe_json_dumps, get_safe_fallback_response, sanitize_data_utf8

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    """BULLETPROOF ROOT ENDPOINT with UTF-8 protection"""
    try:
        safe_message = safe_encode_utf8("JunoPresence Backend is running.")
        return {"message": safe_message}
    except Exception as e:
        logger.error(f"🚨 ROOT ENDPOINT ERROR: {e}")
        return {"message": "Backend is running (safe mode)"}

@app.post("/api/process_audio", response_model=AudioProcessResponse)
async def process_audio(request: Request):
    """BULLETPROOF AUDIO PROCESSING with NUCLEAR UTF-8 PROTECTION"""
    try:
        # SAFE REQUEST PROCESSING
        try:
            request_body = await request.body()
            safe_request_text = safe_encode_utf8(request_body)
            data = safe_json_loads(safe_request_text)
            
            # Handle JSON parsing fallback
            if data.get("safe_fallback"):
                logger.error("🚨 Request JSON parsing failed")
                return AudioProcessResponse(
                    reply=get_safe_fallback_response(),
                    error="Request parsing failed - using safe fallback",
                    audio_url=None,
                    music_command=None,
                    truncated=0
                )
        except Exception as req_err:
            logger.error(f"🚨 REQUEST PROCESSING ERROR: {req_err}")
            return AudioProcessResponse(
                reply=get_safe_fallback_response(),
                error="Request processing failed",
                audio_url=None,
                music_command=None,
                truncated=0
            )
        
        # SAFE DATA EXTRACTION
        try:
            messages = sanitize_data_utf8(data.get("messages", []))
            personality = safe_encode_utf8(data.get("personality", "Base"))
            max_tokens = int(data.get("max_tokens", 150))
        except Exception as extract_err:
            logger.error(f"🚨 DATA EXTRACTION ERROR: {extract_err}")
            messages = []
            personality = "Base"
            max_tokens = 150
        
        # BULLETPROOF AI CALL
        try:
            reply = ai.get_together_ai_reply(messages, personality, max_tokens)
            safe_reply = safe_encode_utf8(reply) if reply else get_safe_fallback_response()
        except Exception as ai_err:
            logger.error(f"🚨 AI CALL ERROR: {ai_err}")
            safe_reply = get_safe_fallback_response()
        
        # SAFE RESPONSE CONSTRUCTION
        try:
            # Generate audio URL if needed (implement this in your ai module)
            # audio_url = ai.generate_audio_url(reply)  # Returns URL string, not raw audio
            audio_url = None  # Currently not generating audio
            
            return AudioProcessResponse(
                reply=safe_reply,
                error=None,
                audio_url=audio_url,  # URL to audio file, never raw binary
                music_command=None,
                truncated=0
            )
        except Exception as response_err:
            logger.error(f"🚨 RESPONSE CONSTRUCTION ERROR: {response_err}")
            return AudioProcessResponse(
                reply=get_safe_fallback_response(),
                error="Response construction failed",
                audio_url=None,
                music_command=None,
                truncated=0
            )
            
    except Exception as critical_err:
        logger.error(f"🚨 CRITICAL PROCESS_AUDIO ERROR: {critical_err}")
        return AudioProcessResponse(
            reply=get_safe_fallback_response(),
            error="Critical error - safe fallback activated",
            audio_url=None,
            music_command=None,
            truncated=0
        )

# Add other endpoints as needed...

# Function to generate audio and return a URL (not the raw audio)
def generate_audio_url(text: str) -> Optional[str]:
    """
    BULLETPROOF AUDIO URL GENERATOR with UTF-8 protection
    Generate audio from text and return a URL to access it.
    Never return raw audio bytes in JSON response.
    
    Args:
        text: Text to convert to speech
        
    Returns:
        URL string to access the audio file, or None if generation failed
    """
    try:
        # SAFE TEXT PROCESSING
        safe_text = safe_encode_utf8(text)
        
        # Implementation would go here
        # 1. Generate audio file
        # 2. Save to disk or cloud storage
        # 3. Return URL to the file
        return None  # Placeholder
    except Exception as e:
        logger.error(f"🚨 AUDIO GENERATION ERROR: {e}")
        return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5020, reload=False)
