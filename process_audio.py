import time
import hashlib
from fastapi import UploadFile, Form
from fastapi.responses import JSONResponse
from redis_setup import performance_monitor
from redis_integration import get_smart_ai_reply_cached
from emotion_intelligence import voice_emotion_analyzer, emotional_adapter

async def process_audio_enhanced(
    audio: UploadFile = None,
    text_input: str = Form(None),
    voice_mode: str = Form("Base"),
    **kwargs
):
    start_time = performance_monitor.start_request()
    
    try:
        emotion_data = None
        original_voice_mode = voice_mode
        
        # Handle input
        if text_input:
            user_text = text_input
        elif audio:
            contents = await audio.read()
            if len(contents) == 0:
                return JSONResponse(content={"reply": "No audio received", "error": "Empty file"})
            
            # Basic emotion analysis on audio
            emotion_data = voice_emotion_analyzer.analyze_voice_emotion(contents)
            
            # Adapt voice mode based on emotion
            if emotion_data and emotion_data.get('confidence', 0) > 0.6:
                voice_mode, reason = emotional_adapter.adapt_voice_mode(
                    emotion_data['emotion'], voice_mode, emotion_data['confidence']
                )
                if voice_mode != original_voice_mode:
                    print(f"🎭 Voice mode adapted: {original_voice_mode} → {voice_mode}")
            
            user_text = f"Audio message processed (detected emotion: {emotion_data.get('emotion', 'neutral')})"
        else:
            return JSONResponse(content={"reply": "Please provide input", "error": "No input"})
        
        # Generate AI response
        messages = [
            {"role": "system", "content": f"You are Juno in {voice_mode} mode."},
            {"role": "user", "content": user_text}
        ]
        
        reply = get_smart_ai_reply_cached(messages, voice_mode)
        
        performance_monitor.end_request(start_time)
        
        return JSONResponse(content={
            "reply": reply,
            "audio_url": None,
            "truncated": False,
            "emotion_data": emotion_data,
            "voice_mode_adapted": voice_mode != original_voice_mode,
            "original_voice_mode": original_voice_mode,
            "adapted_voice_mode": voice_mode,
            "performance": {"total_response_time": round(time.time() - start_time, 3)}
        })
        
    except Exception as e:
        performance_monitor.end_request(start_time)
        return JSONResponse(content={"reply": "Error occurred", "error": str(e)})

print("🎙️ Basic process_audio ready!")
