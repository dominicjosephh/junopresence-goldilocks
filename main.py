]import os
import json
import base64
import requests
import random
import re
import hashlib
import time
from datetime import datetime
from functools import lru_cache
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uvicorn

# Try to import music modules, but don't crash if they're missing
try:
    from music_command_parser import MusicCommandParser, SpotifyController, MusicIntent
    MUSIC_AVAILABLE = True
except ImportError:
    print("⚠️  Music modules not found - music features disabled")
    MUSIC_AVAILABLE = False
    MusicCommandParser = None
    SpotifyController = None
    MusicIntent = None

load_dotenv()
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
voice_id = os.getenv('ELEVENLABS_VOICE_ID')

# Add Spotify credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

MEMORY_FILE = 'memory.json'
FACTS_LIMIT = 20
CHAT_LOG_FILE = "chat_log.json"
AUDIO_DIR = "static"
AUDIO_FILENAME = "juno_response.mp3"
AUDIO_PATH = os.path.join(AUDIO_DIR, AUDIO_FILENAME)

# Performance optimization globals
RESPONSE_CACHE = {}
CACHE_MAX_SIZE = 50
CACHE_TTL = 3600  # 1 hour

# Initialize music intelligence only if available
if MUSIC_AVAILABLE:
    try:
        music_parser = MusicCommandParser()
        spotify_controller = SpotifyController(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
        print("🎵 Music features initialized")
    except Exception as e:
        print(f"⚠️  Music initialization failed: {e}")
        MUSIC_AVAILABLE = False

# Ensure static folder exists
os.makedirs(AUDIO_DIR, exist_ok=True)

def check_ollama_connection():
    """Check if Ollama is running and accessible"""
    try:
        resp = requests.get("http://localhost:11434/api/version", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def get_cache_key(prompt, chat_history_str="", voice_mode="Base"):
    """Generate cache key for responses"""
    combined = f"{prompt}:{chat_history_str}:{voice_mode}"
    return hashlib.md5(combined.encode()).hexdigest()

def get_cached_response(cache_key):
    """Get cached response if it exists and isn't expired"""
    if cache_key in RESPONSE_CACHE:
        response, timestamp = RESPONSE_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            print("🟢 Cache hit - returning cached response")
            return response
        else:
            del RESPONSE_CACHE[cache_key]
    return None

def cache_response(cache_key, response):
    """Cache a response with timestamp"""
    if len(RESPONSE_CACHE) >= CACHE_MAX_SIZE:
        oldest_keys = sorted(RESPONSE_CACHE.keys(),
                           key=lambda k: RESPONSE_CACHE[k][1])[:10]
        for k in oldest_keys:
            del RESPONSE_CACHE[k]
    
    RESPONSE_CACHE[cache_key] = (response, time.time())
    print(f"🟡 Cached response (total cached: {len(RESPONSE_CACHE)})")

def is_music_command(text: str) -> bool:
    """Check if the text is a music-related command"""
    if not MUSIC_AVAILABLE:
        return False
    
    music_keywords = [
        "play", "pause", "stop", "skip", "next", "previous", "music",
        "song", "artist", "album", "playlist", "spotify", "volume",
        "shuffle", "repeat", "by", "put on", "start", "resume"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in music_keywords)

def process_music_command(user_text: str, spotify_access_token: str = None) -> dict:
    """Process a music command and return structured response"""
    if not MUSIC_AVAILABLE:
        return {
            "success": False,
            "message": "Music features are not available right now.",
            "command": None
        }
    
    try:
        command = music_parser.parse_command(user_text)
        print(f"🎵 Parsed music command: {command}")
        
        if command.intent == MusicIntent.UNKNOWN:
            return {
                "success": False,
                "message": "I didn't understand that music command. Try saying something like 'play Training Season by Dua Lipa'",
                "command": None
            }
        
        if not spotify_access_token:
            return {
                "success": False,
                "message": "I need access to your Spotify account to control music. Please connect Spotify first!",
                "command": command.__dict__,
                "requires_spotify_auth": True
            }
        
        # Rest of your music command processing logic...
        # (keeping it the same as your original code)
        
    except Exception as e:
        print(f"❌ Music command processing error: {e}")
        return {
            "success": False,
            "message": "Something went wrong processing your music command. Try again!",
            "error": str(e),
            "command": None
        }

def get_llama3_reply(prompt, chat_history=None, voice_mode="Base"):
    """Get reply from Llama3 with fallback options"""
    # Check cache first
    chat_history_str = str(chat_history) if chat_history else ""
    cache_key = get_cache_key(prompt, chat_history_str, voice_mode)
    
    cached = get_cached_response(cache_key)
    if cached:
        return cached
    
    # Check if Ollama is running
    if not check_ollama_connection():
        fallback_responses = [
            "I'm having trouble connecting to my brain right now! Try restarting Ollama or check if it's running.",
            "Oops! My AI backend seems to be taking a nap. Make sure Ollama is running on your system!",
            "Connection issues on my end! Check if Ollama is running with 'ollama serve' in terminal."
        ]
        return random.choice(fallback_responses)
    
    model = "llama3:8b-instruct-q4_K_M"
    
    full_prompt = prompt
    if chat_history:
        chat_history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history])
        full_prompt = f"{chat_history_text}\nUser: {prompt}"
    
    max_tokens = optimize_response_length(voice_mode, base_length=200)
    
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.8,
            "top_p": 0.9,
            "top_k": 40,
            "num_predict": max_tokens,
            "num_ctx": 2048,
            "repeat_penalty": 1.1,
            "stop": ["\nUser:", "\nHuman:", "\n\n"]
        }
    }
    
    try:
        print(f"🟡 Generating new response with {model} (voice_mode: {voice_mode})")
        start_time = time.time()
        
        resp = requests.post("http://localhost:11434/api/generate",
                           json=payload,
                           timeout=60)
        resp.raise_for_status()
        data = resp.json()
        response = data.get("response", "").strip()
        
        elapsed = time.time() - start_time
        print(f"🟢 Llama3 response generated in {elapsed:.2f} seconds")
        
        cache_response(cache_key, response)
        return response
        
    except requests.exceptions.Timeout:
        print("❌ Llama3/Ollama timeout")
        return "I'm thinking a bit slow right now, bestie! Try asking me again in a moment."
    except requests.exceptions.ConnectionError:
        print("❌ Llama3/Ollama connection error")
        return "Oops! I can't connect to my AI brain. Make sure Ollama is running with 'ollama serve'!"
    except Exception as e:
        print(f"❌ Llama3/Ollama error: {e}")
        return f"Sorry, something went wrong: {str(e)}"

def optimize_response_length(voice_mode, base_length=200):
    """Adjust response length based on voice mode for optimal TTS"""
    length_modifiers = {
        "Sassy": 150,
        "Hype": 180,
        "Shadow": 160,
        "Assert": 140,
        "Challenger": 170,
        "Ritual": 220,
        "Joy": 190,
        "Empathy": 210,
    }
    return length_modifiers.get(voice_mode, base_length)

# Keep all your other functions the same...
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"facts": []}
    with open(MEMORY_FILE, 'r', encoding="utf-8") as f:
        return json.load(f)

def save_memory(memory_data):
    with open(MEMORY_FILE, 'w', encoding="utf-8") as f:
        json.dump(memory_data, f, indent=4, ensure_ascii=False)

def add_fact_to_memory(fact_text):
    memory_data = load_memory()
    if "facts" not in memory_data:
        memory_data["facts"] = []
    memory_data["facts"].insert(0, {
        "fact": fact_text,
        "timestamp": datetime.utcnow().isoformat()
    })
    memory_data["facts"] = memory_data["facts"][:FACTS_LIMIT]
    save_memory(memory_data)

def get_recent_facts(n=3):
    memory_data = load_memory()
    facts = memory_data.get("facts", [])
    return [f["fact"] for f in facts[:n]]

def get_memory_context():
    facts = get_recent_facts(3)
    if not facts:
        return ""
    facts_text = "\n".join(f"- {fact}" for fact in facts)
    return f"Here are some recent facts and memories to keep in mind:\n{facts_text}\n"

def log_chat(user_text, juno_reply):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user_text,
        "juno": juno_reply
    }
    try:
        if not os.path.exists(CHAT_LOG_FILE):
            with open(CHAT_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump([log_entry], f, indent=4, ensure_ascii=False)
        else:
            with open(CHAT_LOG_FILE, "r+", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
                data.append(log_entry)
                f.seek(0)
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.truncate()
    except Exception as e:
        print(f"❌ Chat log failed: {e}")

def clean_reply_for_tts(reply, max_len=400):
    cleaned = re.sub(r'[^\x00-\x7F]+', '', reply)
    if len(cleaned) <= max_len:
        return cleaned, False
    cut = cleaned[:max_len]
    last_period = cut.rfind('. ')
    if last_period > 50:
        return cut[:last_period+1], True
    return cut, True

def generate_tts(reply_text, output_path=AUDIO_PATH):
    if not ELEVENLABS_API_KEY or not voice_id:
        print("❌ ElevenLabs API key or voice ID not configured")
        return None
        
    try:
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
            return output_path
        else:
            print(f"❌ ElevenLabs TTS failed: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"❌ ElevenLabs TTS exception: {e}")
        return None

def preload_model():
    """Preload the model if Ollama is available"""
    if not check_ollama_connection():
        print("⚠️  Ollama not running - skipping model preload")
        return
        
    try:
        print("🟡 Preloading Llama3 model...")
        start_time = time.time()
        
        payload = {
            "model": "llama3:8b-instruct-q4_K_M",
            "prompt": "Hello",
            "stream": False,
            "options": {"num_predict": 1}
        }
        resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        
        if resp.status_code == 200:
            elapsed = time.time() - start_time
            print(f"🟢 Model preloaded successfully in {elapsed:.2f} seconds")
        else:
            print(f"❌ Model preload failed with status: {resp.status_code}")
    except Exception as e:
        print(f"❌ Model preload failed: {e}")

app = FastAPI()

# Mount static directory
app.mount("/static", StaticFiles(directory=AUDIO_DIR), name="static")

@app.on_event("startup")
async def startup_event():
    """Initialize with connection checks"""
    print("🚀 Starting Juno backend...")
    
    # Check services
    if check_ollama_connection():
        print("✅ Ollama connection OK")
        preload_model()
    else:
        print("⚠️  Ollama not running - start with 'ollama serve'")
    
    if ELEVENLABS_API_KEY and voice_id:
        print("✅ ElevenLabs configured")
    else:
        print("⚠️  ElevenLabs not configured")
    
    if MUSIC_AVAILABLE:
        print("✅ Music features available")
    else:
        print("⚠️  Music features disabled")
    
    print("✅ Backend startup complete!")

@app.get("/api/test")
async def test():
    return JSONResponse(content={"message": "Juno backend is running!"})

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(content={
        "status": "running",
        "ollama_connected": check_ollama_connection(),
        "elevenlabs_configured": bool(ELEVENLABS_API_KEY and voice_id),
        "music_available": MUSIC_AVAILABLE
    })

# Keep the rest of your endpoints the same...
@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = None,
    ritual_mode: str = Form(None),
    text_input: str = Form(None),
    chat_history: str = Form(None),
    active_recall: str = Form("true"),
    voice_mode: str = Form("Base"),
    spotify_access_token: str = Form(None)
):
    try:
        user_text = None
        if audio:
            contents = await audio.read()
            with open('temp_audio.m4a', 'wb') as f:
                f.write(contents)
            user_text = "[Voice transcription not implemented]"
        elif text_input:
            user_text = text_input
        else:
            return JSONResponse(content={"reply": None, "error": "No input received"})

        # Parse chat history
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
                if len(history) > 4:
                    history = history[-4:]
            except Exception as e:
                print(f"Chat history parse error: {e}")

        # Check for music commands
        if is_music_command(user_text):
            print(f"🎵 Detected music command: {user_text}")
            music_result = process_music_command(user_text, spotify_access_token)
            
            if music_result["success"]:
                full_reply = music_result["message"]
                
                # Add personality based on voice mode
                if voice_mode == "Sassy":
                    full_reply += " Hope you like my taste in music! 😏"
                elif voice_mode == "Hype":
                    full_reply += " LET'S GO! This is gonna be fire! 🔥"
                elif voice_mode == "Empathy":
                    full_reply += " I hope this music brings you some joy! 💜"
                
                log_chat(user_text, full_reply)
                
                cleaned_reply, was_truncated = clean_reply_for_tts(full_reply, max_len=400)
                tts_result = generate_tts(cleaned_reply, output_path=AUDIO_PATH)
                
                audio_url = f"/static/{AUDIO_FILENAME}" if tts_result else None
                return JSONResponse(content={
                    "reply": full_reply,
                    "audio_url": audio_url,
                    "truncated": was_truncated,
                    "music_command": True,
                    "music_result": music_result,
                    "error": None
                })
            else:
                # Music command failed - include context for regular response
                system_prompt_addition = f"\n\nThe user tried a music command but it failed: {music_result['message']}. Respond helpfully about the music issue."
        else:
            system_prompt_addition = ""

        # Regular conversation handling
        VOICE_MODE_PHRASES = {
            "Sassy": "You are playful, sharp, quick-witted, and throw fun shade, but never sound like a customer service bot.",
            "Empathy": "Respond with warmth, compassion, and gentle encouragement—real, not cliche.",
            "Hype": "Bring hype, energy, and confidence—hype Dom up and make every response lively.",
            "Shadow": "You are smooth, mysterious, and speak with clever, dark humor, but never sound evil or corny.",
            "Assert": "Be bold, direct, and totally honest—never apologetic or robotic.",
            "Challenger": "Sass, challenge, and roast Dom if needed. Don't hold back, but keep it as bestie energy.",
            "Ritual": "Speak with slow, sacred reverence, as if performing a ritual.",
            "Joy": "Overflow with happiness and warmth, make Dom smile."
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

        memory_context = get_memory_context()
        if memory_context:
            full_system_prompt = f"{JUNO_SYSTEM_PROMPT}\n\n{memory_context}{system_prompt_addition}"
        else:
            full_system_prompt = f"{JUNO_SYSTEM_PROMPT}{system_prompt_addition}"

        print("🟢 User Input:", user_text)
        print(f"🟢 Voice Mode: {voice_mode}")

        # Prepare chat context
        messages = [{"role": "system", "content": full_system_prompt}] + history + [{"role": "user", "content": user_text}]
        chat_history_for_prompt = []
        for m in messages:
            if m["role"] == "system":
                # System prompt is not included in chat history for the model prompt
                continue
            chat_history_for_prompt.append({"role": m["role"], "content": m["content"]})

        # Get reply from Llama3 (Ollama)
        juno_reply = get_llama3_reply(user_text, chat_history=chat_history_for_prompt, voice_mode=voice_mode)

        log_chat(user_text, juno_reply)

        cleaned_reply, was_truncated = clean_reply_for_tts(juno_reply, max_len=400)
        tts_result = generate_tts(cleaned_reply, output_path=AUDIO_PATH)
        audio_url = f"/static/{AUDIO_FILENAME}" if tts_result else None

        return JSONResponse(content={
            "reply": juno_reply,
            "audio_url": audio_url,
            "truncated": was_truncated,
            "music_command": False,
            "music_result": None,
            "error": None
        })
    except Exception as e:
        print(f"❌ Error in process_audio: {e}")
        return JSONResponse(content={"reply": None, "error": str(e)})

# Standard FastAPI/uvicorn runner
if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000)
