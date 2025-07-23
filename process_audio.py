import time
import hashlib
import logging
from fastapi import UploadFile, Form
from fastapi.responses import JSONResponse
from redis_setup import performance_monitor
from redis_integration import get_smart_ai_reply_cached
from emotion_intelligence import voice_emotion_analyzer, emotional_adapter
from utils import safe_encode_utf8, safe_decode_response, get_safe_fallback_response, sanitize_data_utf8

from utf8_utils import (
    create_utf8_safe_json_response,
    sanitize_utf8_dict,
    sanitize_ai_response,
    get_emergency_fallback_response,
    log_utf8_debug_info
)
import logging


logger = logging.getLogger(__name__)

async def process_audio_enhanced(
    audio: UploadFile = None,
    text_input: str = Form(None),
    voice_mode: str = Form("Base"),
    **kwargs
):

    """BULLETPROOF AUDIO PROCESSING with NUCLEAR UTF-8 PROTECTION"""

    """
    Enhanced audio processing with comprehensive UTF-8 validation and error handling.
    """

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

        # Sanitize input parameters
        try:
            if text_input:
                text_input = sanitize_ai_response(text_input)
            voice_mode = sanitize_ai_response(voice_mode) if voice_mode else "Base"
        except Exception as sanitize_error:
            logger.error(f"Input sanitization error: {sanitize_error}")
            text_input = "Hello"  # Safe fallback
            voice_mode = "Base"
        
        # Handle input with UTF-8 safety
        try:
            if text_input:
                user_text = text_input
                logger.info(f"Processing text input: {len(user_text)} characters")
                
            elif audio:
                contents = await audio.read()
                if len(contents) == 0:
                    response_data = {
                        "reply": "No audio received", 
                        "error": "Empty audio file",
                        "audio_url": None,
                        "truncated": False,
                        "emotion_data": None,
                        "voice_mode_adapted": False,
                        "original_voice_mode": original_voice_mode,
                        "adapted_voice_mode": voice_mode,
                        "performance": {"total_response_time": 0}
                    }
                    return create_utf8_safe_json_response(response_data, status_code=400)
                
                # Basic emotion analysis on audio with error handling
                try:
                    emotion_data = voice_emotion_analyzer.analyze_voice_emotion(contents)
                    if emotion_data:
                        emotion_data = sanitize_utf8_dict(emotion_data)
                except Exception as emotion_error:
                    logger.warning(f"Emotion analysis error: {emotion_error}")
                    emotion_data = {"emotion": "neutral", "confidence": 0.0}
                
                # Adapt voice mode based on emotion with UTF-8 safety
                try:
                    if emotion_data and emotion_data.get('confidence', 0) > 0.6:
                        voice_mode, reason = emotional_adapter.adapt_voice_mode(
                            emotion_data['emotion'], voice_mode, emotion_data['confidence']
                        )
                        voice_mode = sanitize_ai_response(voice_mode)
                        
                        if voice_mode != original_voice_mode:
                            logger.info(f"Voice mode adapted: {original_voice_mode} → {voice_mode}")
                except Exception as adapt_error:
                    logger.warning(f"Voice mode adaptation error: {adapt_error}")
                    voice_mode = original_voice_mode  # Keep original on error
                
                user_text = f"Audio message processed (detected emotion: {emotion_data.get('emotion', 'neutral')})"
                
            else:
                response_data = {
                    "reply": "Please provide input", 
                    "error": "No input provided",
                    "audio_url": None,
                    "truncated": False,
                    "emotion_data": None,
                    "voice_mode_adapted": False,
                    "original_voice_mode": original_voice_mode,
                    "adapted_voice_mode": voice_mode,
                    "performance": {"total_response_time": 0}
                }
                return create_utf8_safe_json_response(response_data, status_code=400)
                
        except Exception as input_error:
            logger.error(f"Input processing error: {input_error}")
            log_utf8_debug_info(str(input_error), input_error)
            
            emergency_response = get_emergency_fallback_response()
            emergency_response.update({
                "emotion_data": None,
                "voice_mode_adapted": False,
                "original_voice_mode": original_voice_mode,
                "adapted_voice_mode": voice_mode,
                "performance": {"total_response_time": round(time.time() - start_time, 3)}
            })
            return create_utf8_safe_json_response(emergency_response, status_code=500)
        
        # Generate AI response with enhanced error handling
        try:
            messages = [
                {"role": "system", "content": f"You are Juno in {voice_mode} mode."},
                {"role": "user", "content": user_text}
            ]
            
            # Sanitize messages before sending to AI
            sanitized_messages = sanitize_utf8_dict({"messages": messages})["messages"]
            
            reply = get_smart_ai_reply_cached(sanitized_messages, voice_mode)
            
            # Additional sanitization of the reply
            if reply:
                reply = sanitize_ai_response(reply)
            else:
                reply = "I apologize, but I couldn't generate a response. Please try again."
                
        except Exception as ai_error:
            logger.error(f"AI response generation error: {ai_error}")
            log_utf8_debug_info(str(ai_error), ai_error)
            reply = "I encountered an error while generating a response. Please try again."
        
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

        # Prepare final response with comprehensive UTF-8 safety
        response_data = {
            "reply": reply,
            "audio_url": None,  # Keep disabled for UTF-8 safety
            "truncated": False,
            "emotion_data": emotion_data,
            "voice_mode_adapted": voice_mode != original_voice_mode,
            "original_voice_mode": original_voice_mode,
            "adapted_voice_mode": voice_mode,
            "performance": {"total_response_time": round(time.time() - start_time, 3)}
        }
        
        logger.info(f"Successfully processed audio request - Reply: {len(reply)} chars")
        return create_utf8_safe_json_response(response_data)
        
    except Exception as e:
        performance_monitor.end_request(start_time)
        logger.error(f"Critical error in process_audio_enhanced: {e}")
        log_utf8_debug_info(str(e), e)
        
        # Emergency fallback response
        emergency_response = get_emergency_fallback_response()
        emergency_response.update({
            "emotion_data": None,
            "voice_mode_adapted": False,
            "original_voice_mode": original_voice_mode if 'original_voice_mode' in locals() else "Base",
            "adapted_voice_mode": voice_mode if 'voice_mode' in locals() else "Base",
            "performance": {"total_response_time": round(time.time() - start_time, 3)}
        })
        
        return create_utf8_safe_json_response(emergency_response, status_code=500)

print("🎙️ Basic process_audio ready with UTF-8 protection!")
