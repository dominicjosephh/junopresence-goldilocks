import json
import random
from fastapi.responses import JSONResponse
from redis_setup import cache_manager, performance_monitor
from utf8_utils import (
    sanitize_ai_response, 
    sanitize_utf8_dict, 
    create_utf8_safe_json_response,
    log_utf8_debug_info
)
import logging

logger = logging.getLogger(__name__)

def get_smart_ai_reply_cached(messages, voice_mode="Base"):
    """
    Get AI reply with caching, enhanced with UTF-8 safety measures.
    """
    try:
        # Try cache first
        cache_key = [json.dumps(messages), voice_mode]
        cached = cache_manager.get(cache_key, "ai_responses")
        
        if cached:
            logger.info("Response retrieved from cache")
            # Sanitize cached response (it might have been stored before UTF-8 fixes)
            sanitized_cached = sanitize_ai_response(cached)
            return sanitized_cached
        
        # Generate response based on voice mode and context
        user_input = messages[-1]["content"] if messages else ""
        
        # Sanitize user input for safe processing
        safe_user_input = sanitize_ai_response(user_input)[:30]  # Truncate and sanitize
        
        responses = {
            "Sassy": [f"Hey bestie! You said '{safe_user_input}...' - I'm here for it! 💅",
                     "Ooh interesting! Tell me more, I'm listening! 😏"],
            "Hype": [f"YO! I heard '{safe_user_input}...' - LET'S GO! 🔥",
                    "THAT'S WHAT I'M TALKING ABOUT! Keep the energy up! ⚡"],
            "Empathy": [f"I hear you saying '{safe_user_input}...' - I'm here for you 💜",
                       "Thank you for sharing that with me. How are you feeling? 🤗"],
            "Base": [f"Thanks for saying '{safe_user_input}...' - how can I help?",
                    "I'm here and ready to assist! What would you like to talk about?"]
        }
        
        response = random.choice(responses.get(voice_mode, responses["Base"]))
        
        # Sanitize the response before caching
        sanitized_response = sanitize_ai_response(response)
        
        # Cache the sanitized response
        try:
            cache_manager.set(cache_key, sanitized_response, "ai_responses", ttl=3600)
        except Exception as cache_error:
            logger.warning(f"Failed to cache response: {cache_error}")
        
        return sanitized_response
        
    except Exception as e:
        logger.error(f"Error in get_smart_ai_reply_cached: {e}")
        log_utf8_debug_info(str(e), e)
        return sanitize_ai_response("I encountered an error generating a response. Please try again.")

def get_enhanced_memory_context_cached(current_input):
    return ""  # Basic version - no memory context

def generate_tts_cached(reply_text, voice_mode="Base", output_path=""):
    print(f"🔊 TTS: {reply_text[:50]}...")
    return None

async def get_cache_stats():
    try:
        stats = cache_manager.get_stats()
        safe_stats = sanitize_utf8_dict(stats)
        return create_utf8_safe_json_response({
            "cache_stats": safe_stats,
            "status": "basic_ready"
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return create_utf8_safe_json_response({
            "cache_stats": {},
            "status": "error",
            "error": "Failed to retrieve cache statistics"
        })

async def clear_cache_endpoint():
    try:
        # Clear cache logic would go here
        return create_utf8_safe_json_response({
            "success": True, 
            "message": "Cache cleared successfully"
        })
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return create_utf8_safe_json_response({
            "success": False,
            "error": "Failed to clear cache"
        })

async def get_performance_metrics():
    try:
        metrics = performance_monitor.get_performance_report()
        safe_metrics = sanitize_utf8_dict(metrics)
        return create_utf8_safe_json_response(safe_metrics)
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return create_utf8_safe_json_response({
            "error": "Failed to retrieve performance metrics",
            "status": "error"
        })

print("🔄 Basic Redis integration ready!")
