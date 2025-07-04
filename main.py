import torch
from flask import Flask, request, jsonify
from transformers import pipeline, BitsAndBytesConfig
import logging

# --- FIX #2: Configure 4-bit Quantization (NECESSARY for 8GB RAM) ---
# This reduces model memory from ~16GB to ~5GB, allowing it to run.
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
)

# --- FIX #1: Load the Model Globally and ONLY ONimport os
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

# Import our music command parser
from music_command_parser import MusicCommandParser, SpotifyController, MusicIntent

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

# Initialize music intelligence
music_parser = MusicCommandParser()
spotify_controller = SpotifyController(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)

# Ensure static folder exists
os.makedirs(AUDIO_DIR, exist_ok=True)

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
            # Remove expired entry
            del RESPONSE_CACHE[cache_key]
    return None

def cache_response(cache_key, response):
    """Cache a response with timestamp"""
    # Simple cache eviction - clear if too large
    if len(RESPONSE_CACHE) >= CACHE_MAX_SIZE:
        # Remove oldest entries (simple approach)
        oldest_keys = sorted(RESPONSE_CACHE.keys(),
                           key=lambda k: RESPONSE_CACHE[k][1])[:10]
        for k in oldest_keys:
            del RESPONSE_CACHE[k]
    
    RESPONSE_CACHE[cache_key] = (response, time.time())
    print(f"🟡 Cached response (total cached: {len(RESPONSE_CACHE)})")

def is_music_command(text: str) -> bool:
    """Check if the text is a music-related command"""
    music_keywords = [
        "play", "pause", "stop", "skip", "next", "previous", "music", 
        "song", "artist", "album", "playlist", "spotify", "volume",
        "shuffle", "repeat", "by", "put on", "start", "resume"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in music_keywords)

def process_music_command(user_text: str, spotify_access_token: str = None) -> dict:
    """Process a music command and return structured response"""
    try:
        # Parse the command
        command = music_parser.parse_command(user_text)
        print(f"🎵 Parsed music command: {command}")
        
        if command.intent == MusicIntent.UNKNOWN:
            return {
                "success": False,
                "message": "I didn't understand that music command. Try saying something like 'play Training Season by Dua Lipa'",
                "command": None
            }
        
        # If no Spotify token, return instructions
        if not spotify_access_token:
            return {
                "success": False,
                "message": "I need access to your Spotify account to control music. Please connect Spotify first!",
                "command": command.__dict__,
                "requires_spotify_auth": True
            }
        
        # Execute the command based on intent
        if command.intent == MusicIntent.PLAY_SPECIFIC:
            # Search for specific song
            search_query = f"{command.song} {command.artist}" if command.artist else command.song
            track = spotify_controller.search_track(search_query, spotify_access_token)
            
            if track:
                success = spotify_controller.play_track(track["uri"], spotify_access_token)
                if success:
                    return {
                        "success": True,
                        "message": f"Now playing '{track['name']}' by {track['artists'][0]['name']}! 🎵",
                        "track": {
                            "name": track["name"],
                            "artist": track["artists"][0]["name"],
                            "uri": track["uri"]
                        },
                        "command": command.__dict__
                    }
                else:
                    return {
                        "success": False,
                        "message": "Found the song but couldn't play it. Make sure Spotify is open and active!",
                        "command": command.__dict__
                    }
            else:
                return {
                    "success": False,
                    "message": f"Couldn't find '{command.song}' by {command.artist}. Try a different search or check the spelling!",
                    "command": command.__dict__
                }
        
        elif command.intent == MusicIntent.PLAY_ARTIST:
            # Search for artist and play top tracks
            artist = spotify_controller.search_artist(command.artist, spotify_access_token)
            
            if artist:
                success = spotify_controller.play_artist(artist["uri"], spotify_access_token)
                if success:
                    return {
                        "success": True,
                        "message": f"Playing music by {artist['name']}! 🎵",
                        "artist": {
                            "name": artist["name"],
                            "uri": artist["uri"]
                        },
                        "command": command.__dict__
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Found {artist['name']} but couldn't start playback. Make sure Spotify is active!",
                        "command": command.__dict__
                    }
            else:
                return {
                    "success": False,
                    "message": f"Couldn't find the artist '{command.artist}'. Try a different name!",
                    "command": command.__dict__
                }
        
        elif command.intent == MusicIntent.CONTROL:
            # Handle playback control
            success = spotify_controller.control_playback(command.control_action, spotify_access_token)
            
            if success:
                action_messages = {
                    "pause": "Music paused! ⏸️",
                    "skip": "Skipped to the next track! ⏭️",
                    "previous": "Playing the previous track! ⏮️"
                }
                message = action_messages.get(command.control_action, f"Applied {command.control_action}!")
                return {
                    "success": True,
                    "message": message,
                    "command": command.__dict__
                }
            else:
                return {
                    "success": False,
                    "message": f"Couldn't {command.control_action} the music. Make sure Spotify is active!",
                    "command": command.__dict__
                }
        
        elif command.intent == MusicIntent.PLAY_MOOD:
            # Handle mood-based requests (simplified for now)
            mood_queries = {
                "happy": "happy pop upbeat",
                "sad": "sad emotional ballad",
                "chill": "chill ambient relaxed",
                "workout": "workout gym high energy",
                "party": "party dance electronic",
                "focus": "instrumental focus ambient"
            }
            
            query = mood_queries.get(command.mood, "popular music")
            track = spotify_controller.search_track(query, spotify_access_token)
            
            if track:
                success = spotify_controller.play_track(track["uri"], spotify_access_token)
                if success:
                    return {
                        "success": True,
                        "message": f"Playing some {command.mood} music for you! 🎵",
                        "track": {
                            "name": track["name"],
                            "artist": track["artists"][0]["name"]
                        },
                        "command": command.__dict__
                    }
            
            return {
                "success": False,
                "message": f"Couldn't find good {command.mood} music right now. Try being more specific!",
                "command": command.__dict__
            }
        
        else:
            return {
                "success": False,
                "message": "I understand that's a music command, but I'm not sure how to handle it yet!",
                "command": command.__dict__
            }
            
    except Exception as e:
        print(f"❌ Music command processing error: {e}")
        return {
            "success": False,
            "message": "Something went wrong processing your music command. Try again!",
            "error": str(e),
            "command": None
        }

def optimize_response_length(voice_mode, base_length=200):
    """Adjust response length based on voice mode for optimal TTS"""
    length_modifiers = {
        "Sassy": 150,      # Shorter, punchier responses
        "Hype": 180,       # Energetic but not too long
        "Shadow": 160,     # Mysterious and concise
        "Assert": 140,     # Bold and direct
        "Challenger": 170, # Sass but not endless
        "Ritual": 220,     # Can be more elaborate
        "Joy": 190,        # Happy but not overwhelming
        "Empathy": 210,    # Can be more supportive/detailed
    }
    return length_modifiers.get(voice_mode, base_length)

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

def get_llama3_reply(prompt, chat_history=None, voice_mode="Base"):
    # Create cache key including voice_mode
    chat_history_str = str(chat_history) if chat_history else ""
    cache_key = get_cache_key(prompt, chat_history_str, voice_mode)
    
    # Check cache first
    cached = get_cached_response(cache_key)
    if cached:
        return cached
    
    # Use optimized quantized model for much better performance
    model = "llama3:8b-instruct-q4_K_M"  # 3-5x faster than "llama3"
    
    full_prompt = prompt
    if chat_history:
        chat_history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history])
        full_prompt = f"{chat_history_text}\nUser: {prompt}"
    
    # Optimize response length based on voice mode
    max_tokens = optimize_response_length(voice_mode, base_length=200)
    
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.8,
            "top_p": 0.9,
            "top_k": 40,
            "num_predict": max_tokens,  # Optimized based on voice mode
            "num_ctx": 2048,            # Smaller context for speed
            "repeat_penalty": 1.1,
            "stop": ["\nUser:", "\nHuman:", "\n\n"]  # Stop at conversation breaks
        }
    }
    
    try:
        print(f"🟡 Generating new response with {model} (voice_mode: {voice_mode})")
        start_time = time.time()
        
        resp = requests.post("http://localhost:11434/api/generate",
                           json=payload,
                           timeout=60)  # Reduced from 120 to 60 seconds
        resp.raise_for_status()
        data = resp.json()
        response = data.get("response", "").strip()
        
        # Log timing for performance monitoring
        elapsed = time.time() - start_time
        print(f"🟢 Llama3 response generated in {elapsed:.2f} seconds")
        
        # Cache the response
        cache_response(cache_key, response)
        
        return response
        
    except requests.exceptions.Timeout:
        print("❌ Llama3/Ollama timeout - response taking too long")
        return "I'm thinking a bit slow right now, bestie! Try asking me again in a moment."
    except requests.exceptions.ConnectionError:
        print("❌ Llama3/Ollama connection error - service may be down")
        return "Oops! I'm having trouble connecting to my brain right now. Give me a sec!"
    except Exception as e:
        print(f"❌ Llama3/Ollama error: {e}")
        return "Sorry, something went wrong talking to Llama 3."

def preload_model():
    """Preload the model to eliminate startup delay"""
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

def clear_cache():
    """Clear the response cache"""
    global RESPONSE_CACHE
    RESPONSE_CACHE.clear()
    print("🟡 Response cache cleared")

app = FastAPI()

# Mount static directory to serve audio files
app.mount("/static", StaticFiles(directory=AUDIO_DIR), name="static")

@app.on_event("startup")
async def startup_event():
    """Initialize optimizations when server starts"""
    print("🚀 Starting optimized Juno backend with music AI...")
    preload_model()
    print("✅ Backend optimization complete!")

@app.get("/api/test")
async def test():
    return JSONResponse(content={"message": "Optimized backend with music AI is live!"}, media_type="application/json")

@app.get("/api/cache_stats")
async def cache_stats():
    """Get cache statistics for monitoring"""
    return JSONResponse(content={
        "cached_responses": len(RESPONSE_CACHE),
        "max_cache_size": CACHE_MAX_SIZE,
        "cache_ttl": CACHE_TTL
    }, media_type="application/json")

@app.post("/api/clear_cache")
async def clear_cache_endpoint():
    """Clear the response cache"""
    clear_cache()
    return JSONResponse(content={"message": "Cache cleared successfully"}, media_type="application/json")

@app.get("/api/chat_history")
async def chat_history():
    try:
        with open(CHAT_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content={"history": data}, media_type="application/json")
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, media_type="application/json")

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = None,
    ritual_mode: str = Form(None),
    text_input: str = Form(None),
    chat_history: str = Form(None),
    active_recall: str = Form("true"),
    voice_mode: str = Form("Base"),
    spotify_access_token: str = Form(None)  # Add Spotify token
):
    try:
        user_text = None
        if audio:
            contents = await audio.read()
            with open('temp_audio.m4a', 'wb') as f:
                f.write(contents)
            # Replace with actual Whisper transcription if desired
            user_text = "[Voice transcription is not implemented here]"
        elif text_input:
            user_text = text_input
        else:
            return JSONResponse(content={"reply": None, "error": "❌ No valid input received."}, media_type="application/json")

        # Parse chat_history (limit to last 4)
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
                if len(history) > 4:
                    history = history[-4:]
            except Exception as e:
                print(f"Chat history parse error: {e}")

        # 🎵 MUSIC INTELLIGENCE CHECK 🎵
        if is_music_command(user_text):
            print(f"🎵 Detected music command: {user_text}")
            music_result = process_music_command(user_text, spotify_access_token)
            
            if music_result["success"]:
                # Music command succeeded - return success message
                full_reply = music_result["message"]
                
                # Add some Juno personality to the response
                if voice_mode == "Sassy":
                    full_reply += " Hope you like my taste in music! 😏"
                elif voice_mode == "Hype":
                    full_reply += " LET'S GO! This is gonna be fire! 🔥"
                elif voice_mode == "Empathy":
                    full_reply += " I hope this music brings you some joy! 💜"
                
                log_chat(user_text, full_reply)
                
                # Generate TTS and return
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
                }, media_type="application/json")
            
            else:
                # Music command failed - let Juno explain what went wrong
                error_context = f"The user tried to use a music command but it failed: {music_result['message']}"
                system_prompt_addition = f"\n\nIMPORTANT: {error_context}. Respond helpfully about the music issue."
        else:
            system_prompt_addition = ""

        # Regular conversation handling (non-music or failed music commands)
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

        memory_context = get_memory_context()
        if memory_context:
            full_system_prompt = f"{JUNO_SYSTEM_PROMPT}\n\n{memory_context}{system_prompt_addition}"
        else:
            full_system_prompt = f"{JUNO_SYSTEM_PROMPT}{system_prompt_addition}"

        print("🟢 User Input:", user_text)
        print(f"🟢 Voice Mode: {voice_mode}")

        # Prepare chat context for Llama 3:
        messages = [{"role": "system", "content": full_system_prompt}] + history + [{"role": "user", "content": user_text}]
        chat_history_for_prompt = []
        for m in messages:
            if m["role"] == "system":
                chat_history_for_prompt.append(f"Instructions: {m['content']}")
            elif m["role"] == "user":
                chat_history_for_prompt.append(f"User: {m['content']}")
            elif m["role"] == "assistant":
                chat_history_for_prompt.append(f"Juno: {m['content']}")
        prompt = "\n".join(chat_history_for_prompt)

        # --- Optimized Llama 3 reply (via Ollama API) with caching ---
        gpt_reply = get_llama3_reply(prompt, voice_mode=voice_mode)
        full_reply = gpt_reply

        log_chat(user_text, full_reply)

        # Truncate and clean reply for TTS
        cleaned_reply, was_truncated = clean_reply_for_tts(full_reply, max_len=400)

        tts_result = generate_tts(cleaned_reply, output_path=AUDIO_PATH)

        if not tts_result:
            return JSONResponse(content={
                "reply": full_reply,
                "audio_url": None,
                "truncated": was_truncated,
                "error": "❌ TTS generation failed."
            }, media_type="application/json")

        # Return JSON with reply and audio url (not FileResponse!)
        audio_url = f"/static/{AUDIO_FILENAME}"
        return JSONResponse(content={
            "reply": full_reply,
            "audio_url": audio_url,
            "truncated": was_truncated,
            "music_command": False,
            "error": None
        }, media_type="application/json")

    except Exception as e:
        print(f"❌ Server error: {e}")
        return JSONResponse(content={"reply": None, "audio_url": None, "error": str(e)}, media_type="application/json")

# === UNIVERSAL EXCEPTION HANDLER ===
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    print(f"❌ [Universal Exception] {exc}")
    return JSONResponse(
        status_code=500,
        content={"reply": None, "audio_url": None, "error": f"Server error: {str(exc)}"}
    )

if __name__ == "__main__":
    print("🚀 Starting optimized Juno backend with music AI...")
    uvicorn.run(app, host="0.0.0.0", port=5020)CE ---
print("Initializing model... This may take a few minutes.")
# This pipeline object will be created once and reused for all requests.
try:
    model_pipeline = pipeline(
        "text-generation",
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        model_kwargs={
            "quantization_config": quantization_config,
        },
        device_map="auto",  # Will use CPU if no GPU is available
    )
    print("Model loaded successfully and is ready to accept requests.")
except Exception as e:
    print(f"FATAL: Failed to load the model. Error: {e}")
    # If the model fails to load, the application cannot run.
    exit()


# Initialize the Flask App
app = Flask(__name__)
# Configure logging
logging.basicConfig(level=logging.INFO)

@app.route('/generate', methods=['POST'])
def generate():
    """
    Handles text generation requests.
    Expects a JSON payload with a "prompt" key.
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            app.logger.warning("Request received without a 'prompt' field.")
            return jsonify({'error': 'JSON payload must include a "prompt" key.'}), 400

        prompt = data['prompt']
        # You can add more generation parameters here if needed
        # e.g., max_new_tokens = data.get('max_new_tokens', 256)

        app.logger.info(f"Generating text for prompt: '{prompt[:50]}...'")
        
        # Use the pre-loaded model pipeline
        outputs = model_pipeline(
            prompt,
            max_new_tokens=256,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
        )
        
        generated_text = outputs[0]['generated_text']
        app.logger.info("Successfully generated response.")

        return jsonify({'response': generated_text})

    except Exception as e:
        app.logger.error(f"An error occurred during generation: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.'}), 500

# --- FIX #3: How to Run in Production ---
# This part is for local testing. For production, use Gunicorn.
if __name__ == '__main__':
    # DO NOT use this for production.
    app.run(host='0.0.0.0', port=5000, debug=False)
