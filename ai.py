import os
import json
import requests
from utf8_utils import sanitize_ai_response, log_utf8_debug_info
import logging

logger = logging.getLogger(__name__)

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

def transcribe_with_whisper(audio_path):
    # Use Whisper/OpenAI or your preferred transcription
    import whisper
    model = whisper.load_model("base")  # Or 'small', etc.
    result = model.transcribe(audio_path)
    return result["text"].strip()

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    # Your TogetherAI LLM call as before
    # ...

def generate_tts_audio(text, output_dir):
    # Your ElevenLabs TTS call, returns saved filename (not bytes)
    # ...
    # return filename

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    """
    Calls TogetherAI LLM and returns UTF-8 safe reply text.
    Enhanced with comprehensive UTF-8 validation and error handling.
    """
    system_message = {
        "role": "system",
        "content": (
            "You are a friendly, expressive, and emotionally-aware AI assistant. "
            "Respond to the user in a vivid, relatable, natural style. "
            "If the user asks about feelings or mood, answer in a human, relatable way."
        )
    }
    if not messages or messages[0].get("role") == "system":
        messages = [system_message] + messages

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
    
    try:
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30  # Add timeout to prevent hanging
        )
        response.raise_for_status()
        
        # Parse JSON response with UTF-8 safety
        try:
            data = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as json_error:
            logger.error(f"JSON parsing error from TogetherAI: {json_error}")
            log_utf8_debug_info(response.text, json_error)
            return sanitize_ai_response("I encountered a response parsing error. Please try again.")
        
        # Extract and sanitize the AI reply
        if "choices" in data and data["choices"]:
            raw_reply = data["choices"][0]["message"]["content"]
            
            # Apply aggressive UTF-8 sanitization
            try:
                sanitized_reply = sanitize_ai_response(raw_reply)
                logger.info(f"AI reply successfully sanitized: {len(sanitized_reply)} chars")
                return sanitized_reply
                
            except Exception as sanitize_error:
                logger.error(f"AI response sanitization failed: {sanitize_error}")
                log_utf8_debug_info(raw_reply, sanitize_error)
                return sanitize_ai_response("")  # Empty string will trigger fallback
        else:
            logger.warning("No choices in TogetherAI response")
            return sanitize_ai_response("Sorry, I couldn't generate a response.")
            
    except requests.exceptions.RequestException as req_error:
        logger.error(f"Request error from TogetherAI: {req_error}")
        return sanitize_ai_response(f"I'm having trouble connecting to my AI service. Please try again.")
        
    except Exception as e:
        logger.error(f"Unexpected error in get_together_ai_reply: {e}")
        log_utf8_debug_info(str(e), e)
        return sanitize_ai_response("I encountered an unexpected error. Please try again.")
