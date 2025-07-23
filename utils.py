import os
import requests
import json
import utf8_validation
import logging

logger = logging.getLogger(__name__)

TOGETHER_AI_API_KEY = os.getenv('TOGETHER_AI_API_KEY')
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"
TOGETHER_AI_TIMEOUT = 60  # adjust if you want a different timeout

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    if not TOGETHER_AI_API_KEY:
        logger.warning("No TogetherAI API key found.")
        return "API key not configured."
        
    try:
        # Sanitize input messages
        if messages:
            messages = utf8_validation.sanitize_list(messages)
            
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
        
        logger.info("Making TogetherAI request")
        
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TOGETHER_AI_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and data["choices"]:
                reply = data["choices"][0]["message"]["content"].strip()
                
                # Validate and sanitize the reply
                if not utf8_validation.is_valid_utf8(reply):
                    utf8_validation.log_encoding_issue("utils_together_ai_reply", reply)
                    reply = utf8_validation.sanitize_text(reply)
                
                reply = utf8_validation.sanitize_text(reply)
                logger.info(f"TogetherAI reply: {reply[:50]}...")
                return reply
            else:
                logger.warning("No choices in response! Full data logged")
                return "I couldn't generate a response."
        else:
            error_msg = f"TogetherAI HTTP error: {response.status_code}"
            logger.error(error_msg)
            return "I'm having trouble with my AI service right now."
            
    except requests.exceptions.RequestException as e:
        utf8_validation.log_encoding_issue("utils_together_ai_request", None, e)
        logger.error(f"TogetherAI request error: {e}")
        return "I'm having connection issues with my AI service."
        
    except json.JSONDecodeError as e:
        utf8_validation.log_encoding_issue("utils_together_ai_json", None, e)
        logger.error(f"TogetherAI JSON error: {e}")
        return "I received an invalid response from my AI service."
        
    except Exception as e:
        utf8_validation.log_encoding_issue("utils_together_ai_general", None, e)
        logger.error(f"TogetherAI error: {e}")
        return "I encountered an error while processing your request."
