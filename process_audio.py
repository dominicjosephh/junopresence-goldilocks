import time
import hashlib
import logging
from fastapi import UploadFile, Form
from fastapi.responses import JSONResponse
from redis_setup import performance_monitor
from redis_integration import get_smart_ai_reply_cached
from emotion_intelligence import voice_emotion_analyzer, emotional_adapter
from utils import safe_encode_utf8, safe_decode_response, get_safe_fallback_response, sanitize_data_utf8

logger = logging.getLogger(__name__)

async def process_audio_enhanced(
    audio: UploadFile = None,
    text_input: str = Form(None),
    voice_mode: str = Form("Base"),
    **kwargs
):
    """BULLETPROOF AUDIO PROCESSING with NUCLEAR UTF-8 PROTECTION"""
    start_time = performance_monitor.start_request()
    
    try:
        emotion_data = None
        original_voice_mode = safe_encode_utf8(voice_mode)
        
        # SAFE INPUT HANDLING
        try:
            if text_input:
                user_text = safe_encode_utf8(text_input)
            elif audio:
                # BULLETPROOF AUDIO READING
                try:
                    contents = await audio.read()
                    if len(contents) == 0:
                        return JSONResponse(content={
                            "reply": safe_encode_utf8("No audio received"), 
                            "error": safe_encode_utf8("Empty file")
                        })
                    
                    # SAFE EMOTION ANALYSIS
                    try:
                        emotion_data = voice_emotion_analyzer.analyze_voice_emotion(contents)
                        emotion_data = sanitize_data_utf8(emotion_data) if emotion_data else None
                    except Exception as emotion_err:
                        logger.error(f"🚨 EMOTION ANALYSIS ERROR: {emotion_err}")
                        emotion_data = None
                    
                    # SAFE VOICE MODE ADAPTATION
                    try:
                        if emotion_data and emotion_data.get('confidence', 0) > 0.6:
                            detected_emotion = safe_encode_utf8(emotion_data.get('emotion', 'neutral'))
                            voice_mode, reason = emotional_adapter.adapt_voice_mode(
                                detected_emotion, original_voice_mode, emotion_data['confidence']
                            )
                            voice_mode = safe_encode_utf8(voice_mode)
                            if voice_mode != original_voice_mode:
                                print(f"🎭 Voice mode adapted: {original_voice_mode} → {voice_mode}")
                    except Exception as adapt_err:
                        logger.error(f"🚨 VOICE MODE ADAPTATION ERROR: {adapt_err}")
                        voice_mode = original_voice_mode
                    
                    # SAFE USER TEXT EXTRACTION
                    emotion_text = safe_encode_utf8(emotion_data.get('emotion', 'neutral')) if emotion_data else "neutral"
                    user_text = safe_encode_utf8(f"Audio message processed (detected emotion: {emotion_text})")
                    
                except Exception as audio_err:
                    logger.error(f"🚨 AUDIO PROCESSING ERROR: {audio_err}")
                    return JSONResponse(content={
                        "reply": get_safe_fallback_response(), 
                        "error": safe_encode_utf8("Audio processing failed")
                    })
            else:
                return JSONResponse(content={
                    "reply": get_safe_fallback_response(), 
                    "error": safe_encode_utf8("No input provided")
                })
        except Exception as input_err:
            logger.error(f"🚨 INPUT HANDLING ERROR: {input_err}")
            user_text = safe_encode_utf8("Input processing failed")
            voice_mode = safe_encode_utf8("Base")
        
        # BULLETPROOF AI RESPONSE GENERATION
        try:
            # SAFE MESSAGE CONSTRUCTION
            safe_voice_mode = safe_encode_utf8(voice_mode)
            system_content = safe_encode_utf8(f"You are Juno in {safe_voice_mode} mode.")
            user_content = safe_encode_utf8(user_text)
            
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]
            
            # Sanitize entire message structure
            safe_messages = sanitize_data_utf8(messages)
            
            reply = get_smart_ai_reply_cached(safe_messages, safe_voice_mode)
            safe_reply = safe_encode_utf8(reply) if reply else get_safe_fallback_response()
            
        except Exception as ai_err:
            logger.error(f"🚨 AI RESPONSE ERROR: {ai_err}")
            safe_reply = get_safe_fallback_response()
        
        # SAFE PERFORMANCE MONITORING
        try:
            performance_monitor.end_request(start_time)
            total_time = round(time.time() - start_time, 3)
        except Exception as perf_err:
            logger.error(f"🚨 PERFORMANCE MONITORING ERROR: {perf_err}")
            total_time = 0.0
        
        # BULLETPROOF RESPONSE CONSTRUCTION
        try:
            safe_emotion_data = sanitize_data_utf8(emotion_data) if emotion_data else None
            safe_original_mode = safe_encode_utf8(original_voice_mode)
            safe_adapted_mode = safe_encode_utf8(voice_mode)
            
            response_data = {
                "reply": safe_reply,
                "audio_url": None,
                "truncated": False,
                "emotion_data": safe_emotion_data,
                "voice_mode_adapted": safe_adapted_mode != safe_original_mode,
                "original_voice_mode": safe_original_mode,
                "adapted_voice_mode": safe_adapted_mode,
                "performance": {"total_response_time": total_time}
            }
            
            return JSONResponse(content=response_data)
            
        except Exception as response_err:
            logger.error(f"🚨 RESPONSE CONSTRUCTION ERROR: {response_err}")
            return JSONResponse(content={
                "reply": get_safe_fallback_response(),
                "audio_url": None,
                "truncated": False,
                "error": safe_encode_utf8("Response construction failed"),
                "safe_mode": True
            })
        
    except Exception as critical_err:
        logger.error(f"🚨 CRITICAL PROCESS_AUDIO_ENHANCED ERROR: {critical_err}")
        try:
            performance_monitor.end_request(start_time)
        except:
            pass
        return JSONResponse(content={
            "reply": get_safe_fallback_response(), 
            "error": safe_encode_utf8("Critical error - safe fallback activated"),
            "safe_mode": True
        })

print("🎙️ Basic process_audio ready with UTF-8 protection!")
