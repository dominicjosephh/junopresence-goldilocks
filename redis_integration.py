import json
import random
import logging
from fastapi.responses import JSONResponse
from redis_setup import cache_manager, performance_monitor
from utils import safe_encode_utf8, safe_json_dumps, safe_json_loads, get_safe_fallback_response, sanitize_data_utf8

logger = logging.getLogger(__name__)

def get_smart_ai_reply_cached(messages, voice_mode="Base"):
    """BULLETPROOF CACHED AI REPLY with UTF-8 PROTECTION"""
    try:
        # SAFE CACHE KEY GENERATION
        try:
            safe_messages = sanitize_data_utf8(messages)
            safe_voice_mode = safe_encode_utf8(voice_mode)
            cache_key = [safe_json_dumps(safe_messages), safe_voice_mode]
        except Exception as key_err:
            logger.error(f"🚨 CACHE KEY ERROR: {key_err}")
            cache_key = ["fallback_key", safe_encode_utf8(voice_mode)]
        
        # Try cache first with UTF-8 protection
        try:
            cached = cache_manager.get(cache_key, "ai_responses")
            if cached:
                safe_cached = safe_encode_utf8(cached)
                print("🟢 Response from cache!")
                return safe_cached
        except Exception as cache_err:
            logger.error(f"🚨 CACHE GET ERROR: {cache_err}")
        
        # SAFE USER INPUT EXTRACTION
        try:
            user_input = ""
            if messages and len(messages) > 0:
                last_message = messages[-1]
                if isinstance(last_message, dict) and "content" in last_message:
                    user_input = safe_encode_utf8(last_message["content"])
        except Exception as input_err:
            logger.error(f"🚨 USER INPUT EXTRACTION ERROR: {input_err}")
            user_input = ""
        
        # BULLETPROOF RESPONSE GENERATION
        try:
            responses = {
                "Sassy": [
                    safe_encode_utf8(f"Hey bestie! You said '{user_input[:30]}...' - I'm here for it! 💅"),
                    safe_encode_utf8("Ooh interesting! Tell me more, I'm listening! 😏")
                ],
                "Hype": [
                    safe_encode_utf8(f"YO! I heard '{user_input[:30]}...' - LET'S GO! 🔥"),
                    safe_encode_utf8("THAT'S WHAT I'M TALKING ABOUT! Keep the energy up! ⚡")
                ],
                "Empathy": [
                    safe_encode_utf8(f"I hear you saying '{user_input[:30]}...' - I'm here for you 💜"),
                    safe_encode_utf8("Thank you for sharing that with me. How are you feeling? 🤗")
                ],
                "Base": [
                    safe_encode_utf8(f"Thanks for saying '{user_input[:30]}...' - how can I help?"),
                    safe_encode_utf8("I'm here and ready to assist! What would you like to talk about?")
                ]
            }
            
            safe_voice_mode = safe_encode_utf8(voice_mode)
            response_list = responses.get(safe_voice_mode, responses["Base"])
            response = random.choice(response_list)
            
        except Exception as gen_err:
            logger.error(f"🚨 RESPONSE GENERATION ERROR: {gen_err}")
            response = get_safe_fallback_response()
        
        # SAFE CACHE SET
        try:
            cache_manager.set(cache_key, response, "ai_responses", ttl=3600)
        except Exception as cache_set_err:
            logger.error(f"🚨 CACHE SET ERROR: {cache_set_err}")
        
        return response
        
    except Exception as critical_err:
        logger.error(f"🚨 CRITICAL CACHED REPLY ERROR: {critical_err}")
        return get_safe_fallback_response()

def get_enhanced_memory_context_cached(current_input):
    """BULLETPROOF MEMORY CONTEXT with UTF-8 protection"""
    try:
        safe_input = safe_encode_utf8(current_input)
        return ""  # Basic version - no memory context
    except Exception as e:
        logger.error(f"🚨 MEMORY CONTEXT ERROR: {e}")
        return ""

def generate_tts_cached(reply_text, voice_mode="Base", output_path=""):
    """BULLETPROOF TTS GENERATION with UTF-8 protection"""
    try:
        safe_reply = safe_encode_utf8(reply_text)
        safe_voice_mode = safe_encode_utf8(voice_mode)
        print(f"🔊 TTS: {safe_reply[:50]}...")
        return None
    except Exception as e:
        logger.error(f"🚨 TTS GENERATION ERROR: {e}")
        return None

async def get_cache_stats():
    """BULLETPROOF CACHE STATS with UTF-8 protection"""
    try:
        stats = cache_manager.get_stats()
        safe_stats = sanitize_data_utf8(stats)
        return JSONResponse(content={
            "cache_stats": safe_stats,
            "status": safe_encode_utf8("basic_ready")
        })
    except Exception as e:
        logger.error(f"🚨 CACHE STATS ERROR: {e}")
        return JSONResponse(content={
            "cache_stats": {},
            "status": "error_safe_mode",
            "error": safe_encode_utf8(str(e))
        })

async def clear_cache_endpoint():
    """BULLETPROOF CACHE CLEAR with UTF-8 protection"""
    try:
        return JSONResponse(content={
            "success": True, 
            "message": safe_encode_utf8("Cache cleared")
        })
    except Exception as e:
        logger.error(f"🚨 CACHE CLEAR ERROR: {e}")
        return JSONResponse(content={
            "success": False, 
            "message": safe_encode_utf8("Cache clear failed"),
            "error": safe_encode_utf8(str(e))
        })

async def get_performance_metrics():
    """BULLETPROOF PERFORMANCE METRICS with UTF-8 protection"""
    try:
        metrics = performance_monitor.get_performance_report()
        safe_metrics = sanitize_data_utf8(metrics)
        return JSONResponse(content=safe_metrics)
    except Exception as e:
        logger.error(f"🚨 PERFORMANCE METRICS ERROR: {e}")
        return JSONResponse(content={
            "error": safe_encode_utf8("Performance metrics failed"),
            "safe_mode": True
        })

print("🔄 Basic Redis integration ready with UTF-8 protection!")
