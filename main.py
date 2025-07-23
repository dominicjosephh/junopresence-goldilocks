from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os
import json
import base64
import logging
from starlette.middleware.base import BaseHTTPMiddleware
import datetime

# Import your existing modules
import ai
from convo_mode import router as convo_mode_router  # Your existing convo_mode
from process_audio import process_audio_enhanced  # Your existing process_audio
from music import handle_music_command  # Your existing music module

# Import UTF-8 utilities
from utf8_utils import (
    create_utf8_safe_json_response,
    sanitize_utf8_dict,
    get_emergency_fallback_response,
    log_utf8_debug_info,
    sanitize_ai_response,
    UTF8Utils  # Add this if you implement the class from my utf8_utils
)

# Configure logging

import ai  # This is your ai.py module
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

app = FastAPI(title="JunoPresence Emotion AI Backend", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# UTF-8 Error Handling Middleware
class UTF8ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # Check if it's a binary upload
            content_type = request.headers.get('content-type', '')
            
            # For multipart uploads, let FastAPI handle it
            if 'multipart/form-data' in content_type:
                response = await call_next(request)
                return response
            
            # For JSON requests, try to catch UTF-8 errors early
            if 'application/json' in content_type:
                try:
                    # Try to read the body
                    body = await request.body()
                    # Try to decode as JSON
                    try:
                        json.loads(body)
                    except UnicodeDecodeError as e:
                        logger.error(f"UTF-8 decode error in JSON body: {e}")
                        return JSONResponse(
                            status_code=400,
                            content={
                                "error": "ENCODING_ERROR",
                                "message": "Invalid UTF-8 encoding in request body",
                                "details": f"Error at byte position {e.start}",
                                "solution": "Use base64 encoding for binary data in JSON",
                                "recoverable": True
                            }
                        )
                except Exception as e:
                    logger.error(f"Error reading request body: {e}")
            
            response = await call_next(request)
            return response
            
        except UnicodeDecodeError as e:
            logger.error(f"UTF-8 decode error: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "ENCODING_ERROR",
                    "message": "Invalid UTF-8 encoding detected",
                    "details": str(e),
                    "recoverable": True
                }
            )
        except Exception as e:
            logger.error(f"Middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content=get_emergency_fallback_response()
            )

app.add_middleware(UTF8ErrorHandlingMiddleware)

# Include your existing routers
app.include_router(convo_mode_router)  # Your existing convo_mode endpoints

# Request/Response Models
class AudioProcessRequest(BaseModel):
    messages: List[Dict[str, Any]] = Field(..., description="List of message objects")
    personality: str = Field("Base", description="Personality type for the AI")
    max_tokens: int = Field(150, description="Maximum number of tokens to generate")
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    emotion_context: Optional[Dict[str, Any]] = Field(None, description="Emotion context")
    
    @validator('audio_data')
    def validate_audio_data(cls, v):
        if v:
            try:
                base64.b64decode(v)
                return v
            except Exception as e:
                raise ValueError(f"Invalid base64 audio data: {e}")
        return v

class AudioProcessResponse(BaseModel):
    reply: str
    error: Optional[str] = None
    audio_url: Optional[str] = None
    music_command: Optional[str] = None
    truncated: int = 0
    emotion_data: Optional[Dict[str, Any]] = None
    voice_mode_adapted: Optional[bool] = None

@app.get("/")
async def root():
    return create_utf8_safe_json_response({
        "message": "JunoPresence Backend is running",
        "version": "2.0.0",
        "endpoints": {
            "process_audio": "/api/process_audio",
            "process_audio_enhanced": "/api/process_audio_enhanced",
            "convo_mode": "/api/convo_mode",
            "health": "/health"
        }
    })
    return create_utf8_safe_json_response({"message": "JunoPresence Backend is running."})

@app.get("/health")
async def health_check():
    return create_utf8_safe_json_response({
        "status": "healthy",
        "utf8_handler": "active",
        "timestamp": str(datetime.datetime.now())
    })

# Your existing process_audio endpoint with UTF-8 fixes
@app.post("/api/process_audio", response_model=AudioProcessResponse)
async def process_audio(request: Request):
    """

    Original process_audio endpoint with UTF-8 safety

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
        data = sanitize_utf8_dict(raw_data)
        
        # Extract parameters
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
        audio_data = data.get("audio_data")
        
        # Handle base64 audio if provided
        if audio_data:
            try:
                audio_bytes = base64.b64decode(audio_data)
                # Add placeholder message for audio
                messages.append({
                    "role": "user",
                    "content": f"[Audio message: {len(audio_bytes)} bytes]"
                })
            except Exception as e:
                logger.error(f"Base64 decode error: {e}")
        
        # Sanitize messages
        sanitized_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                sanitized_messages.append(sanitize_utf8_dict(msg))
        
        # Get AI reply
        reply = ai.get_together_ai_reply(sanitized_messages, personality, max_tokens)
        reply = sanitize_ai_response(reply)
        
        # Check for music commands
        music_result = None
        if any(keyword in reply.lower() for keyword in ["play", "pause", "next", "previous", "music"]):
            # Extract Spotify token from request if available
            spotify_token = data.get("spotify_token", "")
            if spotify_token:
                music_result = handle_music_command(reply, spotify_token)
        
        response_data = {
            "reply": reply,
            "error": None,
            "audio_url": None,
            "music_command": music_result.get("command") if music_result else None,
            "truncated": 0
        }
        
        return create_utf8_safe_json_response(response_data)
        
    except Exception as e:
        logger.exception("Critical error in process_audio")
        emergency_response = get_emergency_fallback_response()
        emergency_response["error"] = f"Processing error: {str(e)[:100]}"

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

# Route to your existing enhanced audio processing
@app.post("/api/process_audio_enhanced")
async def process_audio_enhanced_endpoint(
    audio: UploadFile = File(None),
    text_input: str = Form(None),
    voice_mode: str = Form("Base"),
    conversation_id: str = Form(None),
    emotion_context: str = Form("{}")
):
    """
    Route to your existing process_audio_enhanced function
    """
    try:
        # Parse emotion context
        try:
            emotion_dict = json.loads(emotion_context) if emotion_context else {}
        except:
            emotion_dict = {}
        
        # Call your existing function
        result = await process_audio_enhanced(
            audio=audio,
            text_input=text_input,
            voice_mode=voice_mode,
            conversation_id=conversation_id,
            emotion_context=emotion_dict
        )
        
        return result
        
    except Exception as e:
        logger.exception("Error in enhanced audio processing")
        return create_utf8_safe_json_response(
            get_emergency_fallback_response(),
            status_code=500
        )

# Add WebSocket support if you want the real-time conversation mode
try:
    from fastapi import WebSocket
    from conversation_mode import websocket_endpoint
    
    @app.websocket("/ws/conversation/{user_id}")
    async def conversation_websocket(websocket: WebSocket, user_id: str):
        """WebSocket endpoint for real-time conversation mode"""
        await websocket_endpoint(websocket, user_id)
except ImportError:
    logger.info("WebSocket conversation mode not available")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5020,
        reload=True,
        log_level="info"
    )
