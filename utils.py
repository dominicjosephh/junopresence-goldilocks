import os
import requests
import json
from utf8_utils import sanitize_ai_response, log_utf8_debug_info
import logging

logger = logging.getLogger(__name__)

TOGETHER_AI_API_KEY = os.getenv('TOGETHER_AI_API_KEY')
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"
TOGETHER_AI_TIMEOUT = 60  # adjust if you want a different timeout

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    """
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
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        
        logger.info("Making TogetherAI API request")
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TOGETHER_AI_TIMEOUT
        )
        
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
