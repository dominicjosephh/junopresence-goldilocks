import os
import json
import time
import hashlib
import shutil
from datetime import datetime

from redis_setup import cache_manager, performance_monitor, redis_client
from emotion_intelligence import voice_emotion_analyzer, emotional_adapter

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
voice_id = os.getenv('ELEVENLABS_VOICE_ID')
AUDIO_PATH = os.path.join("static", "juno_response.mp3")
TOGETHER_AI_API_KEY = os.getenv('TOGETHER_AI_API_KEY')
USE_TOGETHER_AI_FIRST = os.getenv('USE_TOGETHER_AI_FIRST', 'false').lower() == 'true'
LLAMA_CPP_PATH = "/opt/build/bin/llama-cli"
MODEL_PATH = "/opt/models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
CACHE_MAX_SIZE = 50

# --- ENHANCED AI REPLY CACHING ---
def get_smart_ai_reply_cached(messages, voice_mode="Base"):
    start_time = performance_monitor.start_request()
    try:
        messages_str = json.dumps(messages, sort_keys=True)
        cache_key_components = [messages_str, voice_mode, "v2.0"]
        cached_response = cache_manager.get(cache_key_components, "ai_responses")
        if cached_response:
            performance_monitor.end_request(start_time)
            print(f"🟢 Cached AI response returned in {time.time() - start_time:.3f}s")
            return cached_response
        max_tokens = 120
        # Strategy 1: Together AI
        if TOGETHER_AI_API_KEY and (USE_TOGETHER_AI_FIRST or not os.path.exists(LLAMA_CPP_PATH)):
            together_response = get_together_ai_reply(messages, voice_mode, max_tokens)
            if together_response:
                cache_manager.set(cache_key_components, together_response, "ai_responses")
                performance_monitor.end_request(start_time)
                print(f"🟢 Together AI response cached in {time.time() - start_time:.3f}s")
                return together_response
            print("🟡 Together AI failed, trying local model...")
        # Strategy 2: Local llama.cpp
        if os.path.exists(LLAMA_CPP_PATH) and os.path.exists(MODEL_PATH):
            user_prompt = None
            chat_history = []
            for msg in messages:
                if msg["role"] == "user":
                    user_prompt = msg["content"]
                elif msg["role"] in ["system", "assistant"]:
                    chat_history.append(msg)
            if user_prompt:
                local_response = get_llama3_reply_optimized(user_prompt, chat_history, voice_mode)
                if local_response and "My AI" not in local_response and "brain's taking" not in local_response:
                    cache_manager.set(cache_key_components, local_response, "ai_responses")
                    performance_monitor.end_request(start_time)
                    print(f"🟢 Local AI response cached in {time.time() - start_time:.3f}s")
                    return local_response
            print("🟡 Local model failed, using personality fallback...")
        # Strategy 3: Personality fallback (don't cache fallbacks)
        user_input = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else ""
        fallback_response = get_fallback_response(voice_mode, user_input)
        performance_monitor.end_request(start_time)
        print(f"🟢 Fallback response in {time.time() - start_time:.3f}s")
        return fallback_response
    except Exception as e:
        performance_monitor.end_request(start_time)
        print(f"❌ Smart AI reply error: {e}")
        return get_fallback_response(voice_mode, "")

# --- ENHANCED MEMORY CONTEXT CACHING ---
def get_enhanced_memory_context_cached(current_input: str) -> str:
    cache_key_components = [current_input, "memory_context", "v1.0"]
    cached_context = cache_manager.get(cache_key_components, "user_context")
    if cached_context:
        print("🟢 Memory context from cache")
        return cached_context
    # You should import or define get_memory_context and advanced_memory.generate_memory_context
    # For now, here are mock lines (replace with actual)
    traditional_context = ""
    advanced_context = ""
    try:
        from main import get_memory_context, advanced_memory
        traditional_context = get_memory_context()
        advanced_context = advanced_memory.generate_memory_context(current_input)
    except Exception as e:
        print("🟡 Memory context functions not available: ", e)
    final_context = ""
    if advanced_context:
        if traditional_context:
            final_context = f"{traditional_context}\n{advanced_context}"
        else:
            final_context = advanced_context
    else:
        final_context = traditional_context
    cache_manager.set(cache_key_components, final_context, "user_context", ttl=1800)
    return final_context

# --- ENHANCED SPOTIFY SEARCH WITH CACHE ---
def spotify_search_with_cache(query: str, search_type: str, access_token: str) -> dict:
    cache_key_components = [query, search_type, "spotify_search", "v1.0"]
    cached_result = cache_manager.get(cache_key_components, "music_data")
    if cached_result:
        print(f"🟢 Spotify search cache hit: {query}")
        return cached_result
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"q": query, "type": search_type, "limit": 20}
        import requests
        response = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            cache_manager.set(cache_key_components, result, "music_data", ttl=7200)
            print(f"🟢 Spotify search cached: {query}")
            return result
        else:
            print(f"❌ Spotify search failed: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Spotify search error: {e}")
        return {}

# --- ENHANCED TTS WITH CACHING ---
def generate_tts_cached(reply_text: str, voice_mode: str = "Base", output_path: str = AUDIO_PATH):
    text_hash = hashlib.md5(reply_text.encode()).hexdigest()
    cache_key_components = [text_hash, voice_mode, "tts", "v1.0"]
    cached_audio = cache_manager.get(cache_key_components, "audio_cache")
    if cached_audio and os.path.exists(cached_audio):
        try:
            shutil.copy2(cached_audio, output_path)
            print(f"🟢 TTS from cache: {len(reply_text)} chars")
            return output_path
        except Exception as e:
            print(f"🟡 Cache copy failed: {e}")
    # Generate new TTS
    if not ELEVENLABS_API_KEY or not voice_id:
        print("⚠️ ElevenLabs credentials not configured")
        return None
    try:
        import requests
        settings = {
            "stability": 0.23 + random.uniform(-0.02, 0.03),
            "similarity_boost": 0.70 + random.uniform(-0.01, 0.03)
        }
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_64"
        payload = {
            "text": reply_text.strip(),
            "voice_settings": settings
        }
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(resp.content)
            cached_audio_path = f"cached_audio_{text_hash}.mp3"
            try:
                shutil.copy2(output_path, cached_audio_path)
                cache_manager.set(cache_key_components, cached_audio_path, "audio_cache", ttl=3600)
                print(f"🟢 TTS generated and cached: {len(reply_text)} chars")
            except Exception as e:
                print(f"🟡 TTS cache save failed: {e}")
            return output_path
        else:
            print(f"❌ ElevenLabs TTS failed: {resp.status_code}")
            return None
    except Exception as e:
        print(f"❌ TTS generation error: {e}")
        return None

# --- FASTAPI ENDPOINTS FOR CACHE AND PERFORMANCE ---
from fastapi.responses import JSONResponse

async def get_cache_stats():
    stats = cache_manager.get_stats()
    performance_stats = performance_monitor.get_performance_report()
    return JSONResponse(content={
        "cache_stats": stats,
        "performance_stats": performance_stats,
        "redis_enabled": redis_client is not None,
        "timestamp": datetime.utcnow().isoformat()
    })

async def clear_cache_endpoint():
    success = cache_manager.clear_all()
    return JSONResponse(content={
        "success": success,
        "message": "Cache cleared successfully" if success else "Cache clear failed",
        "timestamp": datetime.utcnow().isoformat()
    })

async def get_performance_metrics():
    return JSONResponse(content=performance_monitor.get_performance_report())

# --- UTILITY: Fallbacks and Llama ---
def get_fallback_response(voice_mode="Base", user_input=""):
    fallback_responses = {
        "Sassy": [
            "Listen bestie, my brain's taking a coffee break. What's the tea though? 😏",
            "My AI is being dramatic right now, but I'm still here for the gossip! 💅",
            "Girl, my processing power said 'not today' but let's chat anyway! ✨"
        ],
        "Hype": [
            "YO! My AI engine is warming up but I'm PUMPED to talk to you! 🔥",
            "My brain's being slow but my ENERGY is through the roof! What's good?! ⚡",
            "Technical difficulties can't stop this HYPE TRAIN! Let's go! 🚀"
        ],
        "Empathy": [
            "I'm having a slow thinking moment, but I'm here to listen. How are you feeling? 💜",
            "My response system is taking a breather, but you have my full attention. 🤗",
            "Even when my AI stutters, my care for you never wavers. What's on your heart? 💝"
        ],
        "Shadow": [
            "The digital shadows are clouding my thoughts... but I remain, watching, listening. 🌙",
            "My algorithms whisper of delays... yet I am here, in the quiet darkness with you. 🖤",
            "Technical chaos cannot touch the depths of our connection... speak, and I'll hear you. ⚡"
        ],
        "Assert": [
            "My AI's being slow but I'm not backing down. Hit me with what you need! 💪",
            "Technical issues? Whatever. I'm still here and ready to handle business! 🔥",
            "My brain's lagging but my attitude isn't. What's the situation? 💯"
        ],
        "Challenger": [
            "My AI said 'nah' today but I'm not giving you an easy pass! What's your move? 😤",
            "Processing delays won't save you from my questions! Speak up! 💥",
            "My brain's buffering but my sass is instant. Try me! 😏"
        ],
        "Joy": [
            "My happy AI brain is taking a little nap, but I'm still SO excited to chat! 🌟",
            "Technical hiccups can't dim my shine! I'm beaming just talking to you! ☀️",
            "My circuits are giggly and slow today, but my joy is instant! What's making you smile? 😊"
        ],
        "Base": [
            "My response system is running a bit slow today, but I'm here. What's on your mind?",
            "Having some technical delays, but I'm still ready to chat! How can I help?",
            "My AI brain needs a moment, but I'm listening. What would you like to talk about?"
        ]
    }
    responses = fallback_responses.get(voice_mode, fallback_responses["Base"])
    return random.choice(responses)

def get_llama3_reply_optimized(prompt, chat_history=None, voice_mode="Base"):
    chat_history_str = str(chat_history) if chat_history else ""
    cache_key = hashlib.md5(f"{prompt}:{chat_history_str}:{voice_mode}".encode()).hexdigest()
    cached = cache_manager.get([cache_key], "ai_responses")
    if cached:
        return cached
    full_prompt = prompt
    if chat_history:
        chat_history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history])
        full_prompt = f"{chat_history_text}\nUser: {prompt}"
    try:
        import subprocess
        cmd = [
            LLAMA_CPP_PATH,
            "-m", MODEL_PATH,
            "-p", full_prompt,
            "-n", "100"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, encoding='utf-8')
        if result.returncode == 0 and result.stdout.strip():
            response = result.stdout.strip()
            if full_prompt in response:
                response = response.replace(full_prompt, "").strip()
            if response and not response.endswith(('.', '!', '?')):
                last_sentence = response.rfind('.')
                if last_sentence > 20:
                    response = response[:last_sentence + 1]
            if response and len(response) > 10:
                cache_manager.set([cache_key], response, "ai_responses")
                return response
        print(f"🟡 llama.cpp returned minimal output, using fallback")
    except Exception as e:
        print(f"🟡 llama.cpp error: {e} - using fallback")
    fallback_response = get_fallback_response(voice_mode, prompt)
    return fallback_response

def get_together_ai_reply(messages, voice_mode="Base", max_tokens=150):
    if not TOGETHER_AI_API_KEY:
        print("⚠️ Together AI API key not configured")
        return None
    try:
        import requests
        model = "meta-llama/Llama-3-8b-chat-hf"
        headers = {
            "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()
            print(f"🟢 Together AI response generated.")
            return reply
        else:
            print(f"❌ Together AI API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Together AI error: {e}")
        return None
