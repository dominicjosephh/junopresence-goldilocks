from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os
import ai  # This is your ai.py module
import logging

# Import UTF-8 validation and middleware
from utf8_validator import safe_json_dumps, create_safe_error_response, log_utf8_debug_info, utf8_logger
from utf8_middleware import UTF8ErrorMiddleware

load_dotenv()

app = FastAPI()

# Add UTF-8 error handling middleware FIRST (before CORS)
app.add_middleware(UTF8ErrorMiddleware)

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
    """
    Process audio with comprehensive UTF-8 error handling and validation.
    """
    try:
        # Get request data with UTF-8 validation
        data = await request.json()
        
        # Log request data for debugging
        log_utf8_debug_info(str(data), "process_audio request data")
        
        messages = data.get("messages", [])
        personality = data.get("personality", "Base")
        max_tokens = data.get("max_tokens", 150)
        
        utf8_logger.info(f"Processing audio request: {len(messages)} messages, personality: {personality}")
        
        # Call your LLM/AI function from ai.py with UTF-8 handling
        reply = ai.get_together_ai_reply(messages, personality, max_tokens)
        
        # Validate and sanitize the reply
        if reply is None:
            reply = "Sorry, I couldn't generate a response due to a technical issue."
        
        # Log the reply for UTF-8 debugging
        log_utf8_debug_info(reply, "AI reply")
        
        # Generate audio URL if needed (implement this in your ai module)
        # audio_url = ai.generate_audio_url(reply)  # Returns URL string, not raw audio
        audio_url = None  # Currently not generating audio
        
        # Create response with UTF-8 validation
        response_data = AudioProcessResponse(
            reply=reply,
            error=None,
            audio_url=audio_url,  # URL to audio file, never raw binary
            music_command=None,
            truncated=0
        )
        
        utf8_logger.debug("Successfully created AudioProcessResponse")
        return response_data
        
    except UnicodeDecodeError as e:
        utf8_logger.error(f"UTF-8 decode error in process_audio: {e}")
        error_response = create_safe_error_response(
            f"UTF-8 decode error: {e.reason} at position {e.start}"
        )
        return AudioProcessResponse(**error_response)
        
    except UnicodeEncodeError as e:
        utf8_logger.error(f"UTF-8 encode error in process_audio: {e}")
        error_response = create_safe_error_response(
            f"UTF-8 encode error: {e.reason} at position {e.start}"
        )
        return AudioProcessResponse(**error_response)
        
    except Exception as e:
        utf8_logger.error(f"General error in process_audio: {e}")
        # Check if this might be a UTF-8 related error
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in [
            'utf-8', 'utf8', 'unicode', 'decode', 'encode', 
            'invalid continuation byte', 'invalid start byte'
        ]):
            utf8_logger.error(f"Detected UTF-8 related error: {e}")
            error_response = create_safe_error_response(
                f"Encoding error during audio processing: {str(e)[:100]}..."
            )
        else:
            error_response = create_safe_error_response(
                f"Error processing audio: {str(e)[:100]}..."
            )
        
        return AudioProcessResponse(**error_response)

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
