"""
UTF-8 Validation and Sanitization Utility

This module provides comprehensive UTF-8 validation, sanitization, and error handling
to prevent UTF-8 codec decode errors in JSON responses and other text processing.

Addresses issues with invalid continuation bytes (0xe2, 0xf1) and invalid start bytes (0x9b).
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Union, Tuple

# Configure logging for UTF-8 debugging
utf8_logger = logging.getLogger('utf8_validator')

def is_valid_utf8(data: Union[str, bytes]) -> bool:
    """
    Check if data contains valid UTF-8 encoding.
    
    Args:
        data: String or bytes to validate
        
    Returns:
        bool: True if valid UTF-8, False otherwise
    """
    try:
        if isinstance(data, bytes):
            data.decode('utf-8')
        elif isinstance(data, str):
            data.encode('utf-8')
        return True
    except UnicodeDecodeError:
        return False
    except UnicodeEncodeError:
        return False

def sanitize_utf8(data: Union[str, bytes], replacement: str = '�') -> str:
    """
    Sanitize data to ensure valid UTF-8 encoding.
    
    Args:
        data: Input data to sanitize
        replacement: Character to use for invalid bytes (default: �)
        
    Returns:
        str: Valid UTF-8 string with invalid bytes replaced
    """
    try:
        if isinstance(data, bytes):
            # Use 'replace' error handling to substitute invalid bytes
            return data.decode('utf-8', errors='replace')
        elif isinstance(data, str):
            # Re-encode and decode to catch any encoding issues
            return data.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        else:
            return str(data)
    except Exception as e:
        utf8_logger.warning(f"Sanitization fallback for type {type(data)}: {e}")
        return replacement

def analyze_utf8_errors(data: bytes) -> Tuple[bool, list]:
    """
    Analyze bytes for UTF-8 errors and provide detailed information.
    
    Args:
        data: Bytes to analyze
        
    Returns:
        Tuple[bool, list]: (is_valid, list of error details)
    """
    errors = []
    try:
        data.decode('utf-8')
        return True, []
    except UnicodeDecodeError as e:
        error_info = {
            'error_type': e.reason,
            'start_pos': e.start,
            'end_pos': e.end,
            'invalid_bytes': data[e.start:e.end].hex(),
            'context_before': data[max(0, e.start-10):e.start].hex(),
            'context_after': data[e.end:e.end+10].hex()
        }
        errors.append(error_info)
        utf8_logger.debug(f"UTF-8 error analysis: {error_info}")
        return False, errors

def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Safely serialize data to JSON with UTF-8 validation and fallback.
    
    Args:
        data: Data to serialize
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        str: JSON string with guaranteed valid UTF-8
    """
    try:
        # Recursively sanitize the data
        sanitized_data = sanitize_data_structure(data)
        
        # Set ensure_ascii=False to preserve Unicode characters
        kwargs.setdefault('ensure_ascii', False)
        
        json_str = json.dumps(sanitized_data, **kwargs)
        
        # Validate the resulting JSON string
        if not is_valid_utf8(json_str):
            utf8_logger.warning("JSON output contains invalid UTF-8, applying sanitization")
            json_str = sanitize_utf8(json_str)
            
        return json_str
        
    except Exception as e:
        utf8_logger.error(f"JSON serialization error: {e}")
        # Create a safe error response
        error_response = {
            "reply": "Error: Unable to generate valid response due to encoding issues",
            "error": "UTF-8 encoding error during JSON serialization",
            "details": str(e)
        }
        return json.dumps(error_response, ensure_ascii=True)

def sanitize_data_structure(data: Any) -> Any:
    """
    Recursively sanitize data structures to ensure UTF-8 compatibility.
    
    Args:
        data: Data structure to sanitize
        
    Returns:
        Any: Sanitized data structure
    """
    if isinstance(data, dict):
        return {sanitize_data_structure(k): sanitize_data_structure(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data_structure(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_data_structure(item) for item in data)
    elif isinstance(data, str):
        return sanitize_utf8(data)
    elif isinstance(data, bytes):
        return sanitize_utf8(data)
    else:
        return data

def log_utf8_debug_info(data: Union[str, bytes], context: str = ""):
    """
    Log detailed UTF-8 debugging information.
    
    Args:
        data: Data to analyze
        context: Context description for logging
    """
    if isinstance(data, bytes):
        is_valid, errors = analyze_utf8_errors(data)
        utf8_logger.info(f"UTF-8 Debug [{context}]: Valid={is_valid}, Errors={len(errors)}")
        for error in errors:
            utf8_logger.info(f"  Error: {error}")
    elif isinstance(data, str):
        try:
            encoded = data.encode('utf-8')
            utf8_logger.info(f"UTF-8 Debug [{context}]: String length={len(data)}, Bytes={len(encoded)}")
        except Exception as e:
            utf8_logger.error(f"UTF-8 Debug [{context}]: Encoding error: {e}")

def create_safe_error_response(error_message: str, original_error: Optional[Exception] = None) -> Dict[str, Any]:
    """
    Create a safe error response with guaranteed UTF-8 compatibility.
    
    Args:
        error_message: Error message to include
        original_error: Original exception that caused the error
        
    Returns:
        Dict: Safe error response structure
    """
    safe_message = sanitize_utf8(str(error_message))
    
    response = {
        "reply": "",
        "error": safe_message,
        "audio_url": None,
        "music_command": None,
        "truncated": 0
    }
    
    if original_error:
        response["error_details"] = sanitize_utf8(str(original_error))
        
    return response

def setup_utf8_logging(level: int = logging.INFO) -> None:
    """
    Set up UTF-8 specific logging configuration.
    
    Args:
        level: Logging level
    """
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s [UTF-8] %(levelname)s: %(message)s'
    )
    handler.setFormatter(formatter)
    utf8_logger.addHandler(handler)
    utf8_logger.setLevel(level)
    utf8_logger.propagate = False

# Initialize UTF-8 logging
setup_utf8_logging()