import os
import json
import requests
import utf8_validation
import logging

logger = logging.getLogger(__name__)

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    """
    Calls TogetherAI LLM and returns only reply text (never binary).
    All text is validated for UTF-8 encoding safety.
    """
    try:
        # Sanitize input messages
        if messages:
            messages = utf8_validation.sanitize_list(messages)
        
        system_message = {
            "role": "system",
            "content": utf8_validation.sanitize_text(
                "You are a friendly, expressive, and emotionally-aware AI assistant. "
                "Respond to the user in a vivid, relatable, natural style. "
                "If the user asks about feelings or mood, answer in a human, relatable way."
            )
        }
        
        if not messages or messages[0].get("role") != "system":
            messages = [system_message] + (messages or [])

        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.3",
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        logger.info("Making request to TogetherAI API")
        
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Safely parse the reply
        if "choices" in data and data["choices"]:
            reply = data["choices"][0]["message"]["content"]
            
            # Validate and sanitize the reply
            if not utf8_validation.is_valid_utf8(reply):
                utf8_validation.log_encoding_issue("together_ai_reply", reply)
                reply = utf8_validation.sanitize_text(reply)
            
            # Ensure reply is a safe string
            reply = utf8_validation.sanitize_text(reply)
            
            logger.info(f"Received valid UTF-8 reply: {reply[:100]}...")
            return reply
        else:
            logger.warning("No choices in TogetherAI response")
            return "Sorry, I couldn't generate a response."
            
    except requests.exceptions.RequestException as e:
        error_msg = f"API request error: {str(e)}"
        utf8_validation.log_encoding_issue("together_ai_request", None, e)
        logger.error(error_msg)
        return "I'm having trouble connecting to my AI service right now."
        
    except json.JSONDecodeError as e:
        utf8_validation.log_encoding_issue("together_ai_json", None, e)
        logger.error(f"JSON decode error: {e}")
        return "I received an invalid response from my AI service."
        
    except Exception as e:
        utf8_validation.log_encoding_issue("together_ai_general", None, e)
        logger.error(f"Unexpected error in get_together_ai_reply: {e}")
        return "I encountered an unexpected error while processing your request."
