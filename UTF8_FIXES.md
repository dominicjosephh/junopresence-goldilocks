# UTF-8 Encoding Fixes for JunoPresence

This document outlines the UTF-8 encoding fixes implemented to prevent "utf-8 codec can't decode byte" errors in JSON responses.

## Problem

The application was experiencing UTF-8 encoding errors with messages like:
```
utf-8 codec can't decode byte 0xe0 in position 198: invalid continuation byte
```

This occurred when binary data or improperly encoded text was being included in JSON responses.

## Solution Overview

The fix involves comprehensive UTF-8 validation and sanitization at multiple levels:

1. **Input Sanitization**: All user inputs are sanitized before processing
2. **Output Validation**: All responses are validated before JSON serialization
3. **Error Handling**: Safe error responses that never leak binary data
4. **Logging**: Comprehensive logging for debugging encoding issues

## Files Modified

### Core UTF-8 Validation Module
- **`utf8_validation.py`** (NEW): Core utilities for UTF-8 validation and sanitization

### Application Layer
- **`main.py`**: Added UTF-8 validation middleware and safe response handling
- **`ai.py`**: Enhanced AI response processing with UTF-8 validation
- **`utils.py`**: Updated TogetherAI integration with UTF-8 safety
- **`speech.py`**: Added UTF-8 validation for speech transcription
- **`memory.py`**: Ensured database operations use UTF-8 encoding
- **`redis_integration.py`**: Added UTF-8 validation for cached responses
- **`process_audio.py`**: Enhanced audio processing with UTF-8 safety

### Test Files
- **`test_utf8_fixes.py`** (NEW): Unit tests for UTF-8 validation
- **`test_api_utf8.py`** (NEW): API endpoint tests for UTF-8 safety

## Key Features

### 1. UTF-8 Validation Utilities (`utf8_validation.py`)

```python
# Check if text is valid UTF-8
is_valid_utf8(text) -> bool

# Sanitize text to ensure UTF-8 safety
sanitize_text(text) -> str

# Recursively sanitize dictionaries and lists
sanitize_dict(data) -> dict
sanitize_list(data) -> list

# Create JSON-safe responses
safe_json_response(data) -> dict

# Create safe error responses
create_safe_error_response(error_msg, details) -> dict
```

### 2. Middleware Protection

The FastAPI application now includes middleware that:
- Catches encoding errors before they reach the client
- Returns safe error responses for any encoding issues
- Logs encoding problems for debugging

### 3. Input Sanitization

All user inputs are sanitized:
- Text inputs are validated and cleaned
- Binary data is never included in JSON responses
- Invalid UTF-8 sequences are replaced with safe characters

### 4. Database Safety

Database operations now ensure UTF-8 safety:
- Explicit UTF-8 encoding pragma for SQLite
- Text sanitization before database storage
- Safe error handling for database operations

### 5. API Response Validation

All API responses are validated:
- JSON serializability is tested before sending
- Invalid responses are replaced with safe error messages
- Binary data is converted to safe string representations

## Usage Examples

### Basic Text Sanitization
```python
import utf8_validation

# Sanitize potentially problematic text
safe_text = utf8_validation.sanitize_text(user_input)

# Check if text is valid UTF-8
if utf8_validation.is_valid_utf8(text):
    process_text(text)
```

### Safe API Response Creation
```python
# Create a safe JSON response
response_data = {
    "reply": ai_response,
    "metadata": some_data
}

safe_response = utf8_validation.safe_json_response(response_data)
return JSONResponse(content=safe_response)
```

### Error Handling
```python
try:
    # Process request
    result = process_user_request(data)
except Exception as e:
    # Log the error safely
    utf8_validation.log_encoding_issue("process_request", data, e)
    
    # Return safe error response
    return utf8_validation.create_safe_error_response(
        "Processing error", 
        "An error occurred while processing your request"
    )
```

## Testing

Run the UTF-8 validation tests:

```bash
# Test the UTF-8 validation utilities
python test_utf8_fixes.py

# Test the API endpoints (requires server running)
python test_api_utf8.py
```

Start the server for API testing:
```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 5020
```

## Logging

The application now logs encoding issues with context:
- Error location and context
- Problematic data (safely truncated)
- Exception details
- Timestamp and severity

## Backwards Compatibility

These changes are backwards compatible:
- Existing API endpoints continue to work
- Response format remains the same
- Only the internal handling of text data has changed

## Validation Checklist

- [x] All text inputs are sanitized before processing
- [x] All API responses are validated for UTF-8 safety
- [x] Binary data is never included in JSON responses
- [x] Error messages are UTF-8 safe
- [x] Database operations use explicit UTF-8 encoding
- [x] AI API responses are validated and sanitized
- [x] Comprehensive error handling prevents data leaks
- [x] Logging helps debug encoding issues
- [x] Unit tests validate the fixes
- [x] API tests ensure endpoint safety

## Future Considerations

1. **Performance**: The sanitization adds minimal overhead but could be optimized if needed
2. **Monitoring**: Consider adding metrics for encoding errors
3. **Configuration**: UTF-8 validation could be made configurable if needed
4. **Extensions**: The validation utilities can be extended for other encoding formats

This implementation ensures that the JunoPresence application will never return invalid UTF-8 data in JSON responses, preventing the encoding errors that were previously occurring.