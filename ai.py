import os
import json
import requests
from utf8_validator import sanitize_utf8, log_utf8_debug_info, is_valid_utf8, utf8_logger

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    """
    Calls TogetherAI LLM and returns only reply text with comprehensive UTF-8 validation.
    
    Args:
        messages: List of message objects
        personality: AI personality type
        max_tokens: Maximum tokens to generate
        
    Returns:
        str: Sanitized reply text guaranteed to be valid UTF-8
    """
    try:
        # Validate and sanitize input messages
        sanitized_messages = []
        for msg in messages:
            if isinstance(msg, dict) and 'content' in msg:
                sanitized_content = sanitize_utf8(msg['content'])
                sanitized_msg = {**msg, 'content': sanitized_content}
                sanitized_messages.append(sanitized_msg)
                log_utf8_debug_info(sanitized_content, f"Message content: {msg.get('role', 'unknown')}")
            else:
                sanitized_messages.append(msg)
        
        system_message = {
            "role": "system",
            "content": (
                "You are a friendly, expressive, and emotionally-aware AI assistant. "
                "Respond to the user in a vivid, relatable, natural style. "
                "If the user asks about feelings or mood, answer in a human, relatable way."
            )
        }
        
        if not sanitized_messages or sanitized_messages[0].get("role") != "system":
            sanitized_messages = [system_message] + sanitized_messages

        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.3",
            "messages": sanitized_messages,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        utf8_logger.debug(f"Making TogetherAI request with {len(sanitized_messages)} messages")
        
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Validate response encoding
        if response.content:
            log_utf8_debug_info(response.content, "TogetherAI response content")
        
        response.raise_for_status()
        
        # Safely parse JSON response with UTF-8 validation
        try:
            response_text = response.text
            if not is_valid_utf8(response_text):
                utf8_logger.warning("TogetherAI response contains invalid UTF-8, sanitizing...")
                response_text = sanitize_utf8(response_text)
            
            data = json.loads(response_text)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            utf8_logger.error(f"Error parsing TogetherAI response: {e}")
            return "Sorry, I received an invalid response from the AI service."
        
        # Extract and validate reply content
        if "choices" in data and data["choices"]:
            raw_reply = data["choices"][0]["message"]["content"]
            
            # Sanitize the reply to ensure valid UTF-8
            sanitized_reply = sanitize_utf8(raw_reply)
            
            # Log the sanitization result
            if raw_reply != sanitized_reply:
                utf8_logger.warning("AI reply contained invalid UTF-8 characters - sanitized")
                log_utf8_debug_info(raw_reply, "Original AI reply")
                log_utf8_debug_info(sanitized_reply, "Sanitized AI reply")
            
            utf8_logger.debug(f"TogetherAI reply length: {len(sanitized_reply)} characters")
            return sanitized_reply
        else:
            utf8_logger.warning("No choices in TogetherAI response")
            return "Sorry, I couldn't generate a response."
            
    except requests.exceptions.RequestException as e:
        utf8_logger.error(f"TogetherAI request error: {e}")
        return f"Error from TogetherAI: {sanitize_utf8(str(e))}"
        
    except UnicodeDecodeError as e:
        utf8_logger.error(f"UTF-8 decode error in AI processing: {e}")
        return f"Error: Unable to process response due to character encoding issues (position {e.start})"
        
    except UnicodeEncodeError as e:
        utf8_logger.error(f"UTF-8 encode error in AI processing: {e}")
        return f"Error: Unable to encode response due to character encoding issues (position {e.start})"
        
    except Exception as e:
        utf8_logger.error(f"Unexpected error in TogetherAI processing: {e}")
        error_msg = sanitize_utf8(str(e))
        return f"Error from TogetherAI: {error_msg}"
