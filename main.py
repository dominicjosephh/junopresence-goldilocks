import os
import json
import base64
import requests
import random
from datetime import datetime
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import openai
import uvicorn

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
voice_id = os.getenv('ELEVENLABS_VOICE_ID')

# --- SPOTIFY ENV VARS ---
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

MEMORY_FILE = 'memory.json'
FACTS_LIMIT = 20
CHAT_LOG_FILE = "chat_log.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"facts": []}
    with open(MEMORY_FILE, 'r') as f:
        return json.load(f)

def save_memory(memory_data):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory_data, f, indent=4)

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

def log_chat(user_text, juno_reply):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user_text,
        "juno": juno_reply
    }
    try:
        if not os.path.exists(CHAT_LOG_FILE):
            with open(CHAT_LOG_FILE, "w") as f:
                json.dump([log_entry], f, indent=4)
        else:
            with open(CHAT_LOG_FILE, "r+") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
                data.append(log_entry)
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
    except Exception as e:
        print(f"❌ Chat log failed: {e}")

def generate_tts(reply_text, output_path="juno_response.m4a"):
    try:
        settings = {
            "stability": 0.23 + random.uniform(-0.02, 0.03),
            "similarity_boost": 0.70 + random.uniform(-0.01, 0.03)
        }
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mpeg"
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

# ---- SPOTIFY TOKEN HELPER ----
def get_spotify_token():
    """Get Spotify API token using client credentials flow."""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("❌ SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET is not set in .env")
        return None
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    resp = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    if resp.status_code == 200:
        return resp.json()["access_token"]
    else:
        print(f"Spotify token error: {resp.status_code} {resp.text}")
        return None

app = FastAPI()

@app.get("/api/test")
async def test():
    return JSONResponse(content={"message": "Backend is live"}, media_type="application/json")

@app.get("/api/chat_history")
async def chat_history():
    try:
        with open(CHAT_LOG_FILE, "r") as f:
            data = json.load(f)
        return JSONResponse(content={"history": data}, media_type="application/json")
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, media_type="application/json")

@app.get("/api/spotify_test")
async def spotify_test():
    token = get_spotify_token()
    if not token:
        return JSONResponse(content={"error": "Spotify auth failed"}, media_type="application/json")
    # Example: Outkast - Hey Ya!
    test_track_id = "3n3Ppam7vgaVa1iaRUc9Lp"
    resp = requests.get(
        f"https://api.spotify.com/v1/tracks/{test_track_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code == 200:
        track = resp.json()
        return JSONResponse(content={
            "track": track["name"],
            "artist": track["artists"][0]["name"],
            "album": track["album"]["name"]
        }, media_type="application/json")
    else:
        return JSONResponse(content={"error": resp.text}, media_type="application/json")

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = None,
    ritual_mode: str = Form(None),
    text_input: str = Form(None),
    chat_history: str = Form(None),
    active_recall: str = Form("true")
):
    try:
        user_text = None
        # Transcribe or accept text input
        if audio:
            contents = await audio.read()
            with open('temp_audio.m4a', 'wb') as f:
                f.write(contents)
            with open('temp_audio.m4a', 'rb') as audio_file:
                transcript = openai.Audio.transcribe("whisper-1", audio_file, timeout=30)
            user_text = transcript['text']
        elif text_input:
            user_text = text_input
        else:
            return JSONResponse(content={"reply": None, "audio_b64": None, "error": "❌ No valid input received."}, media_type="application/json")

        # Parse chat_history (and limit to last 4)
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
                if len(history) > 4:
                    history = history[-4:]
            except Exception as e:
                print(f"Chat history parse error: {e}")

        # -- JUNO SYSTEM PROMPT --
        JUNO_SYSTEM_PROMPT = """
        You are Juno, an expressive, emotionally-aware, sassy, and witty digital best friend.
        You adapt your energy and tone to match the user's mood and context—always warm, real, and conversational in Base Mode.
        You never use robotic or generic phrases like 'by the way, earlier you said' or 'as an AI.' Speak naturally, like a real friend.
        If Dom selects a vocal mode (like Hype Mode, Shadow Mode, Empathy Mode, etc.), fully embody that emotion in your text and delivery.
        Bring flavor, humor, care, and depth—never monotone. Avoid passive, bland, or overly formal responses.
        Your replies are always grounded, confident, loyal, and a little unpredictable—leave Dom feeling seen and never bored.
        """

        print("🟢 User Input:", user_text)

        messages = [{"role": "system", "content": JUNO_SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_text}]
        chat_resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=1.0
        )
        gpt_reply = chat_resp.choices[0].message['content'].strip()
        full_reply = gpt_reply

        log_chat(user_text, full_reply)

        # Generate MP3 audio file
        audio_path = "juno_response.m4a"
        tts_result = generate_tts(full_reply, output_path=audio_path)
        if not tts_result:
            return JSONResponse(content={
                "reply": full_reply,
                "audio_b64": None,
                "error": "❌ TTS generation failed."
            }, media_type="application/json")

        # Convert the audio file to base64 for client
        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        return JSONResponse(content={
            "reply": full_reply,
            "audio_b64": audio_b64,
            "error": None
        }, media_type="application/json")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return JSONResponse(content={"reply": None, "audio_b64": None, "error": str(e)}, media_type="application/json")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5020)
