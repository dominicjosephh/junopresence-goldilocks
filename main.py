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
from utf8_utils import (
    create_utf8_safe_json_response, 
    sanitize_utf8_dict, 
    get_emergency_fallback_response,
    log_utf8_debug_info,
    sanitize_ai_response
)
import logging

# Configure logging for UTF-8 error tracking
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
    return create_utf8_safe_json_response({"message": "JunoPresence Backend is running."})

@app.post("/api/process_audio", response_model=AudioProcessResponse)
async def process_audio(request: Request):
    """
    Enhanced audio processing endpoint with aggressive UTF-8 validation and error handling.
    Implements comprehensive UTF-8 safety measures to prevent runtime encoding errors.
    """
    try:
        # Parse request data with UTF-8 safety
        try:
            raw_data = await request.json()
        except Exception as json_error:
            logger.error(f"Request JSON parsing error: {json_error}")
            log_utf8_debug_info(str(json_error), json_error)
            
            # Return emergency fallback
            emergency_response = get_emergency_fallback_response()
            emergency_response["error"] = "Request parsing error - please check your input format"
            return create_utf8_safe_json_response(emergency_response, status_code=400)
        
        # Sanitize input data
        try:
            data = sanitize_utf8_dict(raw_data)
        except Exception as sanitize_error:
            logger.error(f"Request data sanitization error: {sanitize_error}")
            emergency_response = get_emergency_fallback_response()
            emergency_response["error"] = "Input data contains invalid characters"
            return create_utf8_safe_json_response(emergency_response, status_code=400)
        
        # Extract parameters with defaults
        messages = data.get("messages", [])
        personality = data.get("personality", "Base")
        max_tokens = data.get("max_tokens", 150)
        
        # Validate and sanitize messages
        if messages:
            try:
                sanitized_messages = []
                for msg in messages:
                    if isinstance(msg, dict):
                        sanitized_msg = sanitize_utf8_dict(msg)
                        sanitized_messages.append(sanitized_msg)
                    else:
                        logger.warning(f"Invalid message format: {type(msg)}")
                messages = sanitized_messages
            except Exception as msg_error:
                logger.error(f"Message sanitization error: {msg_error}")
                messages = [{"role": "user", "content": "Hello"}]  # Safe fallback
        
        # Call AI with enhanced error handling
        try:
            logger.info(f"Processing audio request with {len(messages)} messages")
            reply = ai.get_together_ai_reply(messages, personality, max_tokens)
            
            # Additional sanitization of AI reply (belt and suspenders approach)
            if reply:
                reply = sanitize_ai_response(reply)
            else:
                reply = "I apologize, but I couldn't generate a response. Please try again."
                
        except Exception as ai_error:
            logger.error(f"AI processing error: {ai_error}")
            log_utf8_debug_info(str(ai_error), ai_error)
            reply = "I encountered an error while processing your request. Please try again."
        
        # Generate audio URL if needed (currently disabled for safety)
        audio_url = None  # Keep disabled until audio generation is UTF-8 safe
        
        # Prepare response with comprehensive UTF-8 safety
        response_data = {
            "reply": reply,
            "error": None,
            "audio_url": audio_url,
            "music_command": None,
            "truncated": 0
        }
        
        # Log successful processing
        logger.info(f"Successfully processed audio request - Reply length: {len(reply)}")
        
        return create_utf8_safe_json_response(response_data)
        
    except Exception as e:
        # Catch-all error handler with UTF-8 safety
        logger.error(f"Critical error in process_audio: {e}")
        log_utf8_debug_info(str(e), e)
        
        # Create emergency response
        emergency_response = get_emergency_fallback_response()
        emergency_response["error"] = f"Internal server error: {str(e)[:100]}..."  # Truncate error message
        
        return create_utf8_safe_json_response(emergency_response, status_code=500)

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
