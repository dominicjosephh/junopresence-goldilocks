import json
import random
from fastapi.responses import JSONResponse
from redis_setup import cache_manager, performance_monitor
import utf8_validation
import logging

logger = logging.getLogger(__name__)

def get_smart_ai_reply_cached(messages, voice_mode="Base"):
    try:
        # Sanitize inputs
        if messages:
            messages = utf8_validation.sanitize_list(messages)
        voice_mode = utf8_validation.sanitize_text(voice_mode)
        
        # Try cache first
        cache_key = [json.dumps(messages), voice_mode]
        cached = cache_manager.get(cache_key, "ai_responses")
        if cached:
            # Ensure cached response is UTF-8 safe
            cached = utf8_validation.sanitize_text(cached)
            logger.info("Response from cache!")
            return cached
        
        # Generate response based on voice mode and context
        user_input = messages[-1]["content"] if messages else ""
        user_input = utf8_validation.sanitize_text(user_input)
        
        responses = {
            "Sassy": [f"Hey bestie! You said '{user_input[:30]}...' - I'm here for it! 💅",
                     "Ooh interesting! Tell me more, I'm listening! 😏"],
            "Hype": [f"YO! I heard '{user_input[:30]}...' - LET'S GO! 🔥",
                    "THAT'S WHAT I'M TALKING ABOUT! Keep the energy up! ⚡"],
            "Empathy": [f"I hear you saying '{user_input[:30]}...' - I'm here for you 💜",
                       "Thank you for sharing that with me. How are you feeling? 🤗"],
            "Base": [f"Thanks for saying '{user_input[:30]}...' - how can I help?",
                    "I'm here and ready to assist! What would you like to talk about?"]
        }
        
        response = random.choice(responses.get(voice_mode, responses["Base"]))
        
        # Ensure response is UTF-8 safe
        response = utf8_validation.sanitize_text(response)
        
        # Cache the response
        cache_manager.set(cache_key, response, "ai_responses", ttl=3600)
        return response
        
    except Exception as e:
        utf8_validation.log_encoding_issue("get_smart_ai_reply_cached", locals(), e)
        logger.error(f"Error in cached AI reply: {e}")
        return "I'm having trouble generating a response right now."

def get_enhanced_memory_context_cached(current_input):
    return ""  # Basic version - no memory context

def generate_tts_cached(reply_text, voice_mode="Base", output_path=""):
    print(f"🔊 TTS: {reply_text[:50]}...")
    return None

async def get_cache_stats():
    return JSONResponse(content={
        "cache_stats": cache_manager.get_stats(),
        "status": "basic_ready"
    })

async def clear_cache_endpoint():
    return JSONResponse(content={"success": True, "message": "Cache cleared"})

async def get_performance_metrics():
    return JSONResponse(content=performance_monitor.get_performance_report())

print("🔄 Basic Redis integration ready!")
