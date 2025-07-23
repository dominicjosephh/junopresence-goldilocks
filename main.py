from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os
import ai  # This is your ai.py module
import utf8_validation
import logging

# Configure logging for encoding issues
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

# UTF-8 validation middleware
@app.middleware("http")
async def utf8_validation_middleware(request: Request, call_next):
    """Middleware to ensure all responses contain valid UTF-8 data."""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        # Log the error safely
        utf8_validation.log_encoding_issue("middleware", str(e), e)
        
        # Return a safe error response
        safe_response = utf8_validation.create_safe_error_response(
            "Internal server error", 
            "An encoding error occurred while processing the request"
        )
        return JSONResponse(content=safe_response, status_code=500)

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
        
        # Sanitize input data
        messages = utf8_validation.sanitize_list(messages)
        personality = utf8_validation.sanitize_text(personality)
        
        # Log the request for debugging
        logger.info(f"Processing audio request with personality: {personality}")
        
        # Call your LLM/AI function from ai.py
        reply = ai.get_together_ai_reply(messages, personality, max_tokens)
        
        # Ensure the reply is UTF-8 safe
        if reply:
            reply = utf8_validation.sanitize_text(reply)
        else:
            reply = "I'm sorry, I couldn't generate a response at this time."
        
        # Generate audio URL if needed (implement this in your ai module)
        # audio_url = ai.generate_audio_url(reply)  # Returns URL string, not raw audio
        audio_url = None  # Currently not generating audio
        
        # Create response and validate it's JSON-safe
        response_data = {
            "reply": reply,
            "error": None,
            "audio_url": audio_url,  # URL to audio file, never raw binary
            "music_command": None,
            "truncated": 0
        }
        
        # Ensure the response is UTF-8 safe
        safe_response = utf8_validation.safe_json_response(response_data)
        
        # Validate that the response can be JSON serialized
        if not utf8_validation.validate_json_serializable(safe_response):
            utf8_validation.log_encoding_issue("process_audio_response", safe_response)
            return utf8_validation.create_safe_error_response(
                "Response encoding error", 
                "Failed to create valid JSON response"
            )
        
        return safe_response
        
    except Exception as e:
        # Log the error with context
        utf8_validation.log_encoding_issue("process_audio", data if 'data' in locals() else None, e)
        
        # Return a safe error response
        return utf8_validation.create_safe_error_response(
            "Processing error", 
            "An error occurred while processing your request"
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
