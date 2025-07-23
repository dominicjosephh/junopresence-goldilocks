import os
import requests
import json
import logging
from typing import Any, Optional, Union

# NUCLEAR UTF-8 PROTECTION - Safe encoding/decoding utilities
def safe_encode_utf8(text: Union[str, bytes], fallback: str = "�") -> str:
    """
    EMERGENCY UTF-8 ENCODER - Force any input to valid UTF-8 string
    Handles any encoding issues with safe fallback replacement
    """
    try:
        if isinstance(text, bytes):
            # Try multiple encoding approaches
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    decoded = text.decode(encoding)
                    # Re-encode to UTF-8 to ensure safety
                    return decoded.encode('utf-8', errors='replace').decode('utf-8')
                except UnicodeDecodeError:
                    continue
            # Last resort: replace all problematic bytes
            return text.decode('utf-8', errors='replace')
        elif isinstance(text, str):
            # Ensure string is properly UTF-8 encoded
            return text.encode('utf-8', errors='replace').decode('utf-8')
        else:
            # Convert any other type to string safely
            return str(text).encode('utf-8', errors='replace').decode('utf-8')
    except Exception as e:
        logging.error(f"🚨 CRITICAL UTF-8 ENCODING ERROR: {e}")
        return fallback

def safe_decode_response(response_content: Union[str, bytes]) -> str:
    """
    BULLETPROOF RESPONSE DECODER - Handles any response encoding
    Never fails, always returns valid UTF-8 string
    """
    try:
        if isinstance(response_content, bytes):
            return safe_encode_utf8(response_content)
        else:
            return safe_encode_utf8(response_content)
    except Exception as e:
        logging.error(f"🚨 CRITICAL RESPONSE DECODE ERROR: {e}")
        return "Error: Unable to decode response safely"

def safe_json_loads(text: Union[str, bytes]) -> dict:
    """
    NUCLEAR JSON PARSER - Never fails on UTF-8 issues
    Returns safe dict even with encoding problems
    """
    try:
        safe_text = safe_encode_utf8(text)
        return json.loads(safe_text)
    except json.JSONDecodeError as e:
        logging.error(f"🚨 JSON DECODE ERROR: {e}")
        return {"error": "Invalid JSON format", "safe_fallback": True}
    except Exception as e:
        logging.error(f"🚨 CRITICAL JSON PARSE ERROR: {e}")
        return {"error": f"JSON parsing failed: {str(e)}", "safe_fallback": True}

def safe_json_dumps(data: Any) -> str:
    """
    BULLETPROOF JSON SERIALIZER - Handles any UTF-8 issues
    Always returns valid UTF-8 JSON string
    """
    try:
        # Ensure all strings in data are UTF-8 safe
        safe_data = sanitize_data_utf8(data)
        return json.dumps(safe_data, ensure_ascii=False).encode('utf-8', errors='replace').decode('utf-8')
    except Exception as e:
        logging.error(f"🚨 CRITICAL JSON SERIALIZE ERROR: {e}")
        return json.dumps({"error": f"Serialization failed: {str(e)}", "safe_fallback": True})

def sanitize_data_utf8(data: Any) -> Any:
    """
    RECURSIVE UTF-8 SANITIZER - Cleans all strings in nested data structures
    """
    try:
        if isinstance(data, str):
            return safe_encode_utf8(data)
        elif isinstance(data, bytes):
            return safe_encode_utf8(data)
        elif isinstance(data, dict):
            return {safe_encode_utf8(k): sanitize_data_utf8(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [sanitize_data_utf8(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(sanitize_data_utf8(item) for item in data)
        else:
            return data
    except Exception as e:
        logging.error(f"🚨 CRITICAL DATA SANITIZATION ERROR: {e}")
        return str(data)

# EMERGENCY FALLBACK RESPONSES
SAFE_FALLBACK_RESPONSES = [
    "I'm here to help! How can I assist you today?",
    "Thanks for reaching out! What would you like to talk about?",
    "I'm ready to assist you. What's on your mind?",
    "Hello! I'm here and ready to help with whatever you need.",
    "I appreciate you connecting with me. How can I be of service?"
]

def get_safe_fallback_response() -> str:
    """
    EMERGENCY RESPONSE GENERATOR - Always returns safe UTF-8 response
    """
    import random
    try:
        return random.choice(SAFE_FALLBACK_RESPONSES)
    except Exception:
        return "I'm here to help! How can I assist you today?"

from utf8_utils import sanitize_ai_response, log_utf8_debug_info
import logging

logger = logging.getLogger(__name__)


TOGETHER_AI_API_KEY = os.getenv('TOGETHER_AI_API_KEY')
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"
TOGETHER_AI_TIMEOUT = 60  # adjust if you want a different timeout

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    """

    BULLETPROOF AI REPLY FUNCTION - Never fails on UTF-8 errors
    """
    if not TOGETHER_AI_API_KEY:
        logging.warning("No TogetherAI API key found.")
        return get_safe_fallback_response()

    Enhanced TogetherAI API call with comprehensive UTF-8 safety measures.
    """
    if not TOGETHER_AI_API_KEY:
        logger.warning("No TogetherAI API key found.")
        return sanitize_ai_response("I'm not configured with an API key. Please check the setup.")

    
    try:
        model = "mistralai/Mistral-7B-Instruct-v0.3"
        headers = {
            "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # SANITIZE ALL INPUT DATA
        safe_messages = sanitize_data_utf8(messages)
        
        payload = {
            "model": model,
            "messages": safe_messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        

        # Safe payload logging
        try:
            safe_payload_str = safe_json_dumps(payload)
            print("🟢 TogetherAI PAYLOAD:", safe_payload_str)
        except Exception as log_err:
            print(f"🚨 Payload logging error: {log_err}")

        logger.info("Making TogetherAI API request")

response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TOGETHER_AI_TIMEOUT
        )
        

        # BULLETPROOF RESPONSE PROCESSING
        try:
            # Get response content safely
            response_text = safe_decode_response(response.content)
            print("🟢 TogetherAI RAW RESPONSE:", response_text[:500] + "..." if len(response_text) > 500 else response_text)
            
            if response.status_code == 200:
                data = safe_json_loads(response_text)
                
                # Handle JSON parsing errors
                if data.get("safe_fallback"):
                    logging.error("🚨 JSON parsing failed, using fallback")
                    return get_safe_fallback_response()
                
                if "choices" in data and data["choices"]:
                    reply = safe_encode_utf8(data["choices"][0]["message"]["content"]).strip()
                    print("🟢 TogetherAI reply:", reply[:200] + "..." if len(reply) > 200 else reply)
                    return reply
                else:
                    logging.warning("No choices in response! Using fallback")
                    return get_safe_fallback_response()
            else:
                logging.error(f"TogetherAI HTTP error: {response.status_code}")
                return get_safe_fallback_response()
                
        except Exception as response_err:
            logging.error(f"🚨 RESPONSE PROCESSING ERROR: {response_err}")
            return get_safe_fallback_response()
            
    except Exception as e:
        logging.error(f"🚨 CRITICAL TogetherAI ERROR: {e}")
        return get_safe_fallback_response()
=======
        # Log raw response for debugging (safely)
        try:
            logger.debug(f"TogetherAI response status: {response.status_code}")
            logger.debug(f"TogetherAI response length: {len(response.text)}")
        except Exception as log_error:
            logger.warning(f"Failed to log response details: {log_error}")
        
        if response.status_code == 200:
            try:
                data = response.json()
            except (json.JSONDecodeError, UnicodeDecodeError) as json_error:
                logger.error(f"JSON parsing error from TogetherAI: {json_error}")
                log_utf8_debug_info(response.text, json_error)
                return sanitize_ai_response("I received a malformed response. Please try again.")
            
            if "choices" in data and data["choices"]:
                raw_reply = data["choices"][0]["message"]["content"].strip()
                
                # Apply UTF-8 sanitization
                sanitized_reply = sanitize_ai_response(raw_reply)
                logger.info(f"TogetherAI reply processed: {len(sanitized_reply)} chars")
                return sanitized_reply
            else:
                logger.warning("No choices in TogetherAI response")
                return sanitize_ai_response("I couldn't generate a response. Please try again.")
        else:
            logger.error(f"TogetherAI HTTP error: {response.status_code}")
            return sanitize_ai_response("I'm having trouble with the AI service. Please try again.")
            
    except requests.exceptions.Timeout:
        logger.error("TogetherAI request timeout")
        return sanitize_ai_response("The AI service is taking too long to respond. Please try again.")
        
    except requests.exceptions.RequestException as req_error:
        logger.error(f"TogetherAI request error: {req_error}")
        return sanitize_ai_response("I'm having trouble connecting to the AI service. Please try again.")
        
    except Exception as e:
        logger.error(f"Unexpected error in get_together_ai_reply: {e}")
        log_utf8_debug_info(str(e), e)
        return sanitize_ai_response("I encountered an unexpected error. Please try again.")