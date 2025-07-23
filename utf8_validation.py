"""
UTF-8 validation and sanitization utilities for JunoPresence.

This module provides utilities to ensure all text data is properly UTF-8 encoded
before being included in JSON responses, preventing encoding errors.
"""

import json
import logging
import unicodedata
from typing import Any, Dict, Union, Optional

logger = logging.getLogger(__name__)


def is_valid_utf8(text: Any) -> bool:
    """
    Check if the given text is valid UTF-8.
    
    Args:
        text: Text to validate (will be converted to string)
        
    Returns:
        bool: True if valid UTF-8, False otherwise
    """
    if text is None:
        return True
    
    try:
        if isinstance(text, bytes):
            text.decode('utf-8')
        else:
            str(text).encode('utf-8').decode('utf-8')
        return True
    except (UnicodeDecodeError, UnicodeEncodeError):
        logger.warning(f"Invalid UTF-8 detected in text: {repr(text)[:100]}...")
        return False


def sanitize_text(text: Any, replacement: str = "�") -> str:
    """
    Sanitize text to ensure it's valid UTF-8.
    
    Args:
        text: Text to sanitize
        replacement: Character to use for invalid sequences
        
    Returns:
        str: UTF-8 safe string
    """
    if text is None:
        return ""
    
    try:
        # Convert to string first
        text_str = str(text)
        
        # Try to encode/decode to catch any issues
        text_str.encode('utf-8').decode('utf-8')
        
        # Normalize unicode characters
        text_str = unicodedata.normalize('NFKC', text_str)
        
        # Remove or replace any control characters except common ones
        clean_chars = []
        for char in text_str:
            if char.isprintable() or char in '\n\r\t':
                clean_chars.append(char)
            else:
                clean_chars.append(replacement)
        
        return ''.join(clean_chars)
        
    except (UnicodeDecodeError, UnicodeEncodeError) as e:
        logger.warning(f"UTF-8 sanitization error: {e}, text: {repr(text)[:100]}...")
        # Return a safe fallback
        return str(text).encode('utf-8', errors='replace').decode('utf-8')


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary.
    
    Args:
        data: Dictionary to sanitize
        
    Returns:
        Dict with UTF-8 safe string values
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        # Sanitize the key
        safe_key = sanitize_text(key)
        
        # Sanitize the value based on type
        if isinstance(value, str):
            sanitized[safe_key] = sanitize_text(value)
        elif isinstance(value, dict):
            sanitized[safe_key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[safe_key] = sanitize_list(value)
        elif isinstance(value, bytes):
            # Never include raw bytes in JSON - convert to safe representation
            logger.warning(f"Binary data detected for key '{key}', converting to safe string")
            sanitized[safe_key] = f"<binary data: {len(value)} bytes>"
        else:
            # For other types, convert to string and sanitize
            sanitized[safe_key] = sanitize_text(value)
    
    return sanitized


def sanitize_list(data: list) -> list:
    """
    Recursively sanitize all values in a list.
    
    Args:
        data: List to sanitize
        
    Returns:
        List with UTF-8 safe values
    """
    if not isinstance(data, list):
        return data
    
    sanitized = []
    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_text(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item))
        elif isinstance(item, bytes):
            # Never include raw bytes in JSON
            logger.warning(f"Binary data detected in list, converting to safe string")
            sanitized.append(f"<binary data: {len(item)} bytes>")
        else:
            sanitized.append(sanitize_text(item))
    
    return sanitized


def safe_json_response(data: Any) -> Dict[str, Any]:
    """
    Create a JSON-safe response by sanitizing all text data.
    
    Args:
        data: Data to make JSON-safe
        
    Returns:
        Dict with UTF-8 safe data
    """
    try:
        if isinstance(data, dict):
            return sanitize_dict(data)
        elif isinstance(data, list):
            return {"data": sanitize_list(data)}
        elif isinstance(data, bytes):
            logger.warning("Binary data passed to safe_json_response")
            return {"error": "Binary data cannot be included in JSON response"}
        else:
            return {"data": sanitize_text(data)}
    except Exception as e:
        logger.error(f"Error creating safe JSON response: {e}")
        return {"error": "Internal encoding error", "data": None}


def validate_json_serializable(data: Any) -> bool:
    """
    Test if data can be safely serialized to JSON.
    
    Args:
        data: Data to test
        
    Returns:
        bool: True if serializable, False otherwise
    """
    try:
        json.dumps(data, ensure_ascii=False)
        return True
    except (TypeError, ValueError, UnicodeDecodeError) as e:
        logger.warning(f"JSON serialization validation failed: {e}")
        return False


def create_safe_error_response(error_msg: str, details: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a safe error response that won't cause encoding issues.
    
    Args:
        error_msg: Main error message
        details: Optional additional details
        
    Returns:
        Dict with safe error response
    """
    response = {
        "error": sanitize_text(error_msg),
        "reply": "",
        "audio_url": None,
        "music_command": None,
        "truncated": 0
    }
    
    if details:
        response["details"] = sanitize_text(details)
    
    return response


# Logging helper
def log_encoding_issue(context: str, data: Any, error: Exception = None):
    """
    Log encoding issues for debugging.
    
    Args:
        context: Context where the issue occurred
        data: The problematic data
        error: Optional exception that occurred
    """
    try:
        data_repr = repr(data)[:200] if data is not None else "None"
        error_msg = str(error) if error else "No exception"
        logger.error(f"Encoding issue in {context}: data={data_repr}, error={error_msg}")
    except Exception as log_error:
        logger.error(f"Failed to log encoding issue in {context}: {log_error}")