"""
UTF-8 Error Handling Middleware for FastAPI

This middleware catches and handles UTF-8 encoding errors in FastAPI requests and responses,
providing robust fallback mechanisms and detailed debugging information.
"""

import logging
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from utf8_validator import (
    safe_json_dumps, 
    create_safe_error_response, 
    log_utf8_debug_info, 
    sanitize_utf8,
    utf8_logger
)

class UTF8ErrorMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle UTF-8 encoding errors in FastAPI applications.
    
    Catches UnicodeDecodeError, UnicodeEncodeError, and other encoding-related
    exceptions and provides safe fallback responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle any UTF-8 encoding errors.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint function
            
        Returns:
            Response: Safe response with UTF-8 error handling
        """
        try:
            # Log request information for debugging
            self._log_request_info(request)
            
            # Process the request
            response = await call_next(request)
            
            # Validate response encoding if it's a JSON response
            if hasattr(response, 'body') and response.headers.get('content-type', '').startswith('application/json'):
                self._validate_response_encoding(response)
            
            return response
            
        except UnicodeDecodeError as e:
            utf8_logger.error(f"UnicodeDecodeError in request processing: {e}")
            return self._create_utf8_error_response(
                f"UTF-8 decode error: {e.reason} at position {e.start}",
                e
            )
            
        except UnicodeEncodeError as e:
            utf8_logger.error(f"UnicodeEncodeError in request processing: {e}")
            return self._create_utf8_error_response(
                f"UTF-8 encode error: {e.reason} at position {e.start}",
                e
            )
            
        except Exception as e:
            # Check if this is a UTF-8 related error
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in [
                'utf-8', 'utf8', 'unicode', 'decode', 'encode', 
                'invalid continuation byte', 'invalid start byte'
            ]):
                utf8_logger.error(f"UTF-8 related error: {e}")
                utf8_logger.debug(f"Full traceback: {traceback.format_exc()}")
                return self._create_utf8_error_response(
                    f"Encoding error: {sanitize_utf8(str(e))}",
                    e
                )
            else:
                # Re-raise non-UTF-8 errors
                raise e
    
    def _log_request_info(self, request: Request) -> None:
        """
        Log request information for UTF-8 debugging.
        
        Args:
            request: FastAPI request object
        """
        try:
            url = str(request.url)
            method = request.method
            content_type = request.headers.get('content-type', 'N/A')
            
            utf8_logger.debug(f"Processing request: {method} {url} (Content-Type: {content_type})")
            
            # Log content encoding if available
            if hasattr(request, '_body'):
                log_utf8_debug_info(request._body, f"Request body for {method} {url}")
                
        except Exception as e:
            utf8_logger.warning(f"Error logging request info: {e}")
    
    def _validate_response_encoding(self, response: Response) -> None:
        """
        Validate response encoding for JSON responses.
        
        Args:
            response: FastAPI response object
        """
        try:
            if hasattr(response, 'body') and response.body:
                # Check if the response body is valid UTF-8
                if isinstance(response.body, bytes):
                    try:
                        response.body.decode('utf-8')
                        utf8_logger.debug("Response body UTF-8 validation: OK")
                    except UnicodeDecodeError as e:
                        utf8_logger.warning(f"Response body contains invalid UTF-8: {e}")
                        # Sanitize the response body
                        sanitized_body = response.body.decode('utf-8', errors='replace')
                        response.body = sanitized_body.encode('utf-8')
                        utf8_logger.info("Response body sanitized for UTF-8 compatibility")
                        
        except Exception as e:
            utf8_logger.warning(f"Error validating response encoding: {e}")
    
    def _create_utf8_error_response(self, message: str, original_error: Exception = None) -> JSONResponse:
        """
        Create a safe JSON error response for UTF-8 errors.
        
        Args:
            message: Error message
            original_error: Original exception
            
        Returns:
            JSONResponse: Safe error response
        """
        try:
            error_data = create_safe_error_response(message, original_error)
            
            # Use safe JSON dumps to ensure valid UTF-8
            json_content = safe_json_dumps(error_data)
            
            return JSONResponse(
                status_code=500,
                content=error_data,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-UTF8-Error": "true"
                }
            )
            
        except Exception as e:
            utf8_logger.error(f"Error creating UTF-8 error response: {e}")
            # Absolute fallback - ASCII only response
            return JSONResponse(
                status_code=500,
                content={
                    "reply": "",
                    "error": "Critical UTF-8 encoding error - unable to generate safe response",
                    "audio_url": None,
                    "music_command": None,
                    "truncated": 0
                },
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-UTF8-Error": "critical"
                }
            )

def setup_utf8_debugging() -> None:
    """
    Set up enhanced UTF-8 debugging logging.
    """
    # Add more detailed logging for UTF-8 issues
    utf8_logger.setLevel(logging.DEBUG)
    
    # Log system encoding information
    import sys
    import locale
    
    utf8_logger.info(f"System default encoding: {sys.getdefaultencoding()}")
    utf8_logger.info(f"System filesystem encoding: {sys.getfilesystemencoding()}")
    utf8_logger.info(f"Locale encoding: {locale.getpreferredencoding()}")

# Initialize debugging on import
setup_utf8_debugging()