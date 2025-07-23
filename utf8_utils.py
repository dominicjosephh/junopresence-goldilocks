"""
UTF-8 validation and sanitization utilities for handling AI responses and JSON serialization.
Provides comprehensive UTF-8 error handling to prevent runtime encoding errors.
"""

import json
import logging
import unicodedata
from typing import Any, Dict, Optional, Union
from fastapi.responses import JSONResponse

# Configure logging for UTF-8 issues
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sanitize_utf8_string(text: str, replacement_char: str = "?") -> str:
    """
    Aggressively sanitize a string to ensure it's valid UTF-8.
    
    Args:
        text: Input string that may contain invalid UTF-8 bytes
        replacement_char: Character to replace invalid bytes with
        
    Returns:
        Clean UTF-8 string with invalid bytes replaced
    """
    if not isinstance(text, str):
        text = str(text)
    
    try:
        # First, try encoding and decoding to catch any issues
        encoded = text.encode('utf-8', errors='replace')
        decoded = encoded.decode('utf-8', errors='replace')
        
        # Normalize unicode characters to handle edge cases
        normalized = unicodedata.normalize('NFKC', decoded)
        
        # Replace any remaining problematic characters
        sanitized = ''.join(char if ord(char) < 0x110000 and char.isprintable() or char.isspace() 
                          else replacement_char for char in normalized)
        
        return sanitized
        
    except Exception as e:
        logger.error(f"UTF-8 sanitization error: {e} - Original text length: {len(text)}")
        # Emergency fallback: return safe placeholder
        return f"[Text sanitization failed: {replacement_char * 10}]"

def sanitize_utf8_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary to ensure UTF-8 safety.
    
    Args:
        data: Dictionary that may contain unsafe UTF-8 strings
        
    Returns:
        Dictionary with all strings sanitized for UTF-8
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        # Sanitize the key itself
        safe_key = sanitize_utf8_string(str(key))
        
        # Sanitize the value based on its type
        if isinstance(value, str):
            sanitized[safe_key] = sanitize_utf8_string(value)
        elif isinstance(value, dict):
            sanitized[safe_key] = sanitize_utf8_dict(value)
        elif isinstance(value, list):
            sanitized[safe_key] = [sanitize_utf8_string(item) if isinstance(item, str) 
                                 else sanitize_utf8_dict(item) if isinstance(item, dict) 
                                 else item for item in value]
        else:
            sanitized[safe_key] = value
    
    return sanitized

def validate_utf8_json_safe(data: Any) -> bool:
    """
    Validate that data can be safely serialized to JSON without UTF-8 errors.
    
    Args:
        data: Data to validate for JSON serialization
        
    Returns:
        True if data is safe for JSON serialization, False otherwise
    """
    try:
        json.dumps(data, ensure_ascii=False)
        return True
    except (UnicodeDecodeError, UnicodeEncodeError, TypeError) as e:
        logger.warning(f"JSON serialization validation failed: {e}")
        return False

def create_utf8_safe_json_response(data: Dict[str, Any], status_code: int = 200) -> JSONResponse:
    """
    Create a FastAPI JSONResponse with aggressive UTF-8 safety measures.
    
    Args:
        data: Response data dictionary
        status_code: HTTP status code
        
    Returns:
        JSONResponse with UTF-8 safe content
    """
    try:
        # First, sanitize all string content
        sanitized_data = sanitize_utf8_dict(data)
        
        # Validate it can be JSON serialized
        if not validate_utf8_json_safe(sanitized_data):
            logger.error("Data failed UTF-8 JSON validation even after sanitization")
            sanitized_data = get_emergency_fallback_response()
        
        # Try to create the response
        return JSONResponse(content=sanitized_data, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Critical UTF-8 JSON response error: {e}")
        # Emergency fallback response
        emergency_data = get_emergency_fallback_response()
        return JSONResponse(content=emergency_data, status_code=500)

def get_emergency_fallback_response() -> Dict[str, str]:
    """
    Get a safe emergency fallback response when UTF-8 errors occur.
    
    Returns:
        Safe fallback response dictionary
    """
    return {
        "reply": "I apologize, but I encountered a text encoding error. Please try your request again.",
        "error": "UTF-8 encoding error occurred",
        "audio_url": None,
        "music_command": None,
        "truncated": 0
    }

def log_utf8_debug_info(original_text: str, error: Exception) -> None:
    """
    Log detailed debugging information about UTF-8 errors.
    
    Args:
        original_text: The text that caused the UTF-8 error
        error: The exception that occurred
    """
    try:
        logger.error(f"UTF-8 Error Details:")
        logger.error(f"- Error: {error}")
        logger.error(f"- Text length: {len(original_text)}")
        logger.error(f"- Text type: {type(original_text)}")
        
        # Log problematic byte positions
        try:
            original_text.encode('utf-8')
        except UnicodeEncodeError as ue:
            logger.error(f"- Encoding error at position {ue.start}-{ue.end}: {ue.reason}")
            logger.error(f"- Problematic text segment: {repr(original_text[max(0, ue.start-10):ue.end+10])}")
        
        # Log first 200 chars as repr to see actual bytes
        logger.error(f"- Text preview (first 200 chars): {repr(original_text[:200])}")
        
    except Exception as debug_error:
        logger.error(f"Failed to log UTF-8 debug info: {debug_error}")

def sanitize_ai_response(ai_response: str) -> str:
    """
    Specifically sanitize AI responses which are prone to UTF-8 issues.
    
    Args:
        ai_response: Raw AI response string
        
    Returns:
        Sanitized AI response safe for JSON serialization
    """
    if not ai_response:
        return "I apologize, but I couldn't generate a response. Please try again."
    
    try:
        # Sanitize the response
        sanitized = sanitize_utf8_string(ai_response)
        
        # Ensure it's not empty after sanitization
        if not sanitized.strip():
            return "I apologize, but my response contained formatting issues. Please try again."
        
        return sanitized
        
    except Exception as e:
        logger.error(f"AI response sanitization failed: {e}")
        return "I encountered an error processing my response. Please try again."