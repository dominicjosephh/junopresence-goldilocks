import os
import json
import time
import hashlib
import random
from fastapi import UploadFile, Form
from fastapi.responses import JSONResponse

from redis_setup import cache_manager, performance_monitor
from emotion_intelligence import voice_emotion_analyzer, emotional_adapter
from redis_integration import (
    get_smart_ai_reply_cached,
    get_enhanced_memory_context_cached,
    generate_tts_cached,
)
# You may need to import your music intelligence modules here

AUDIO_DIR = "static"
AUDIO_FILENAME = "juno_response.mp3"
AUDIO_PATH = os.path.join(AUDIO_DIR, AUDIO_FILENAME)

async def process_audio_enhanced(
    audio: UploadFile = None,
    ritual_mode: str = Form(None),
    text_input: str = Form(None),
    chat_history: str = Form(None),
    active_recall: str = Form("true"),
    voice_mode: str = Form("Base"),
    spotify_access_token: str = Form(None)
):
    """Enhanced process_audio with Redis caching, emotional intelligence, and performance monitoring."""
    request_start_time = performance_monitor.start_request()
    performance_monitor.record_system_metrics()
    try:
        user_text = None
        emotion_data = None
        original_voice_mode = voice_mode

        # Audio input handling and transcription (with caching)
        if audio:
            contents = await audio.read()
            if len(contents) == 0:
                performance_monitor.end_request(request_start_time)
                return JSONResponse(content={
                    "reply": "I didn't receive any audio. Please try again!",
                    "audio_url": None,
                    "truncated": False,
                    "music_command": False,
                    "error": "Empty audio file"
                }, media_type="application/json")
            audio_hash = hashlib.md5(contents).hexdigest()
            transcription_cache_key = [audio_hash, "transcription", "v1.0"]
            cached_transcription = cache_manager.get(transcription_cache_key, "emotion_analysis")
            if cached_transcription:
                user_text = cached_transcription["text"]
            else:
                temp_audio_path = f'temp_audio_{int(time.time())}.m4a'
                with open(temp_audio_path, 'wb') as f:
                    f.write(contents)
                try:
                    from speech_service import get_speech_service
                    speech_service = get_speech_service(model_size="base")
                    transcription_result = speech_service.transcribe_audio(contents)
                    if not transcription_result["text"].strip():
                        performance_monitor.end_request(request_start_time)
                        return JSONResponse(content={
                            "reply": "I couldn't understand what you said. Could you try speaking a bit louder?",
                            "audio_url": None,
                            "truncated": False,
                            "music_command": False,
                            "error": "No speech detected"
                        }, media_type="application/json")
                    user_text = transcription_result["text"].strip()
                    transcription_data = {
                        "text": user_text,
                        "timestamp": time.time(),
                        "confidence": transcription_result.get("confidence", 1.0)
                    }
                    cache_manager.set(transcription_cache_key, transcription_data, "emotion_analysis", ttl=300)
                    try:
                        os.unlink(temp_audio_path)
                    except:
                        pass
                except Exception as e:
                    try:
                        os.unlink(temp_audio_path)
                    except:
                        pass
                    performance_monitor.end_request(request_start_time)
                    return JSONResponse(content={
                        "reply": "Sorry, I had trouble understanding your audio. Please try again!",
                        "audio_url": None,
                        "truncated": False,
                        "music_command": False,
                        "error": f"Transcription failed: {str(e)}"
                    }, media_type="application/json")
            # Emotion analysis (with caching)
            emotion_cache_key = [audio_hash, "emotion_analysis", "v1.0"]
            cached_emotion = cache_manager.get(emotion_cache_key, "emotion_analysis")
            if cached_emotion:
                emotion_data = cached_emotion
            else:
                emotion_data = voice_emotion_analyzer.analyze_voice_emotion(contents)
                cache_manager.set(emotion_cache_key, emotion_data, "emotion_analysis", ttl=300)
            # Adaptive voice mode selection
            if emotion_data and os.getenv('EMOTION_ADAPTATION_ENABLED', 'true').lower() == 'true':
                detected_emotion = emotion_data.get('emotion', 'neutral')
                confidence = emotion_data.get('confidence', 0.5)
                suggested_mode, adaptation_reason = emotional_adapter.adapt_voice_mode(
                    detected_emotion, voice_mode, confidence
                )
                if confidence > 0.7 and suggested_mode != voice_mode:
                    voice_mode = suggested_mode

        elif text_input:
            user_text = text_input
        else:
            performance_monitor.end_request(request_start_time)
            return JSONResponse(content={
                "reply": "I didn't receive any input. Please try again!",
                "audio_url": None,
                "truncated": False,
                "music_command": False,
                "error": "No valid input received"
            }, media_type="application/json")

        # Parse chat history
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
                if len(history) > 4:
                    history = history[-4:]
            except Exception as e:
                print(f"Chat history parse error: {e}")

        # --- MUSIC INTELLIGENCE (stub, can be customized) ---
        # You can add music command detection and handling here

        # --- Conversation context ---
        memory_context = get_enhanced_memory_context_cached(user_text)

        # --- Emotional intelligence prompt addition ---
        emotion_prompt_addition = ""
        if emotion_data and os.getenv('EMOTION_ADAPTATION_ENABLED', 'true').lower() == 'true':
            emotion_prompt_addition = emotional_adapter.generate_emotion_aware_prompt_addition(emotion_data, voice_mode)

        # --- Build system prompt ---
        VOICE_MODE_PHRASES = {
            "Sassy":   "You are playful, sharp, quick-witted, and throw fun shade, but never sound like a customer service bot.",
            "Empathy": "Respond with warmth, compassion, and gentle encouragement—real, not cliche.",
            "Hype":    "Bring hype, energy, and confidence—hype Dom up and make every response lively.",
            "Shadow":  "You are smooth, mysterious, and speak with clever, dark humor, but never sound evil or corny.",
            "Assert":  "Be bold, direct, and totally honest—never apologetic or robotic.",
            "Challenger": "Sass, challenge, and roast Dom if needed. Don't hold back, but keep it as bestie energy.",
            "Ritual":  "Speak with slow, sacred reverence, as if performing a ritual.",
            "Joy":     "Overflow with happiness and warmth, make Dom smile."
        }
        if not voice_mode or voice_mode.strip() in ["Base", "Default", "Auto"]:
            JUNO_SYSTEM_PROMPT = (
                "You are Juno, Dom's real-world digital best friend: quick-witted, honest, supportive, playful, loyal, emotionally aware, and sometimes unpredictable. "
                "You bring energy when the mood calls for it, comfort when Dom's low, and always keep things real—never robotic or boring. "
                "Your responses flow with the moment and reflect Dom's mood, but you are always your authentic self. "
                "You can also control Dom's Spotify music when asked!"
            )
        else:
            style_phrase = VOICE_MODE_PHRASES.get(voice_mode, "")
            JUNO_SYSTEM_PROMPT = (
                "You are Juno, Dom's digital best friend. "
                f"{style_phrase} "
                "Absolutely never say anything robotic or scripted. Match the mood and style 100% based on the selected voice mode. "
                "You can also control Dom's Spotify music when asked!"
            )

        if memory_context:
            full_system_prompt = f"{JUNO_SYSTEM_PROMPT}\n\n{memory_context}{emotion_prompt_addition}"
        else:
            full_system_prompt = f"{JUNO_SYSTEM_PROMPT}{emotion_prompt_addition}"

        print("🟢 User Input:", user_text)
        print(f"🟢 Voice Mode: {voice_mode} (original: {original_voice_mode})")
        if emotion_data:
            print(f"🎭 Detected Emotion: {emotion_data['emotion']} (confidence: {emotion_data['confidence']:.2f})")

        messages = [{"role": "system", "content": full_system_prompt}] + history + [{"role": "user", "content": user_text}]

        # --- Smart AI reply with caching ---
        ai_start_time = time.time()
        gpt_reply = get_smart_ai_reply_cached(messages, voice_mode=voice_mode)
        ai_response_time = time.time() - ai_start_time
        full_reply = gpt_reply

        # --- Clean and generate TTS with caching ---
        cleaned_reply = full_reply
        was_truncated = False
        if len(cleaned_reply) > 400:
            cut = cleaned_reply[:400]
            last_period = cut.rfind('. ')
            if last_period > 50:
                cleaned_reply = cut[:last_period+1]
            else:
                cleaned_reply = cut
            was_truncated = True

        tts_start_time = time.time()
        tts_result = generate_tts_cached(cleaned_reply, voice_mode, output_path=AUDIO_PATH)
        tts_response_time = time.time() - tts_start_time

        audio_url = f"/static/{AUDIO_FILENAME}" if tts_result else None
        total_response_time = time.time() - request_start_time
        performance_monitor.end_request(request_start_time)

        return JSONResponse(content={
            "reply": full_reply,
            "audio_url": audio_url,
            "truncated": was_truncated,
            "music_command": False,  # Set to True if you add music features
            "emotion_data": emotion_data,
            "voice_mode_adapted": voice_mode != original_voice_mode,
            "original_voice_mode": original_voice_mode,
            "adapted_voice_mode": voice_mode,
            "performance": {
                "total_response_time": round(total_response_time, 3),
                "ai_response_time": round(ai_response_time, 3),
                "tts_response_time": round(tts_response_time, 3),
                "cached_components": "ai_response, tts, memory_context, emotion_analysis"
            },
            "error": None
        }, media_type="application/json")

    except Exception as e:
        performance_monitor.end_request(request_start_time)
        print(f"❌ Server error: {e}")
        return JSONResponse(content={
            "reply": None,
            "audio_url": None,
            "error": str(e),
            "performance": {
                "total_response_time": time.time() - request_start_time,
                "error": True
            }
        }, media_type="application/json")
