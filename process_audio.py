import time
import hashlib
from fastapi import UploadFile, Form
from fastapi.responses import JSONResponse
from redis_setup import performance_monitor
from redis_integration import get_smart_ai_reply_cached
from emotion_intelligence import voice_emotion_analyzer, emotional_adapter
import utf8_validation
import logging

logger = logging.getLogger(__name__)

async def process_audio_enhanced(
    audio: UploadFile = None,
    text_input: str = Form(None),
    voice_mode: str = Form("Base"),
    **kwargs
):
    start_time = performance_monitor.start_request()
    
    try:
        emotion_data = None
        original_voice_mode = utf8_validation.sanitize_text(voice_mode)
        
        # Handle input
        if text_input:
            user_text = utf8_validation.sanitize_text(text_input)
        elif audio:
            contents = await audio.read()
            if len(contents) == 0:
                return JSONResponse(content=utf8_validation.create_safe_error_response(
                    "No audio received", "Empty file"
                ))
            
            # Basic emotion analysis on audio
            emotion_data = voice_emotion_analyzer.analyze_voice_emotion(contents)
            
            # Adapt voice mode based on emotion
            if emotion_data and emotion_data.get('confidence', 0) > 0.6:
                voice_mode, reason = emotional_adapter.adapt_voice_mode(
                    emotion_data['emotion'], voice_mode, emotion_data['confidence']
                )
                if voice_mode != original_voice_mode:
                    logger.info(f"Voice mode adapted: {original_voice_mode} → {voice_mode}")
            
            emotion_text = emotion_data.get('emotion', 'neutral')
            user_text = f"Audio message processed (detected emotion: {emotion_text})"
        else:
            return JSONResponse(content=utf8_validation.create_safe_error_response(
                "Please provide input", "No input"
            ))
        
        # Generate AI response
        messages = [
            {"role": "system", "content": f"You are Juno in {voice_mode} mode."},
            {"role": "user", "content": user_text}
        ]
        
        reply = get_smart_ai_reply_cached(messages, voice_mode)
        reply = utf8_validation.sanitize_text(reply)
        
        performance_monitor.end_request(start_time)
        
        response_data = {
            "reply": reply,
            "audio_url": None,
            "truncated": False,
            "emotion_data": emotion_data,
            "voice_mode_adapted": voice_mode != original_voice_mode,
            "original_voice_mode": original_voice_mode,
            "adapted_voice_mode": voice_mode,
            "performance": {"total_response_time": round(time.time() - start_time, 3)}
        }
        
        # Ensure the response is UTF-8 safe
        safe_response = utf8_validation.safe_json_response(response_data)
        
        return JSONResponse(content=safe_response)
        
    except Exception as e:
        performance_monitor.end_request(start_time)
        utf8_validation.log_encoding_issue("process_audio_enhanced", locals(), e)
        return JSONResponse(content=utf8_validation.create_safe_error_response(
            "Processing error", "An error occurred while processing your request"
        ))

logger.info("🎙️ Enhanced process_audio ready with UTF-8 validation!")
