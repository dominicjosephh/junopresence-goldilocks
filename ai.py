import os
import json
import requests
import logging
from utils import safe_encode_utf8, safe_decode_response, safe_json_loads, get_safe_fallback_response, sanitize_data_utf8

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    """
    BULLETPROOF AI REPLY FUNCTION with NUCLEAR UTF-8 PROTECTION
    Calls TogetherAI LLM and returns only safe UTF-8 reply text (never binary).
    NEVER FAILS - Always returns a safe response
    """
    try:
        # EMERGENCY FALLBACK if no API key
        if not TOGETHER_AI_API_KEY:
            logging.warning("🚨 No TogetherAI API key found - using fallback")
            return get_safe_fallback_response()
        
        # SAFE SYSTEM MESSAGE CREATION
        system_message = {
            "role": "system",
            "content": safe_encode_utf8(
                "You are a friendly, expressive, and emotionally-aware AI assistant. "
                "Respond to the user in a vivid, relatable, natural style. "
                "If the user asks about feelings or mood, answer in a human, relatable way."
            )
        }
        
        # SANITIZE ALL INPUT MESSAGES
        safe_messages = sanitize_data_utf8(messages) if messages else []
        
        if not safe_messages or safe_messages[0].get("role") != "system":
            safe_messages = [system_message] + safe_messages

        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.3",
            "messages": safe_messages,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # BULLETPROOF API CALL with UTF-8 PROTECTION
        try:
            response = requests.post(
                f"{TOGETHER_AI_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30  # Reduced timeout for faster fallback
            )
            response.raise_for_status()
            
            # SAFE RESPONSE PROCESSING
            response_text = safe_decode_response(response.content)
            data = safe_json_loads(response_text)
            
            # Handle JSON parsing fallback
            if data.get("safe_fallback"):
                logging.error("🚨 TogetherAI response JSON parsing failed")
                return get_safe_fallback_response()
            
            # SAFE REPLY EXTRACTION
            if "choices" in data and data["choices"]:
                reply_content = data["choices"][0]["message"]["content"]
                safe_reply = safe_encode_utf8(reply_content)
                return safe_reply
            else:
                logging.warning("🚨 No choices in TogetherAI response")
                return get_safe_fallback_response()
                
        except requests.exceptions.RequestException as req_err:
            logging.error(f"🚨 TogetherAI REQUEST ERROR: {req_err}")
            return get_safe_fallback_response()
        except Exception as api_err:
            logging.error(f"🚨 TogetherAI API ERROR: {api_err}")
            return get_safe_fallback_response()
            
    except Exception as critical_err:
        logging.error(f"🚨 CRITICAL AI FUNCTION ERROR: {critical_err}")
        return get_safe_fallback_response()
