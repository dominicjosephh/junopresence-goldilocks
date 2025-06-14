import os
import json
import base64
import requests
import re
from datetime import datetime
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import openai
import uvicorn
import random

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

def generate_tts(reply_text):
    try:
        settings = {
            "stability": 0.23 + random.uniform(-0.02, 0.03),
            "similarity_boost": 0.70 + random.uniform(-0.01, 0.03)
        }
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
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
            return base64.b64encode(resp.content).decode('utf-8')
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
            return JSONResponse(content={"reply": "❌ No valid input received.", "tts": ""}, media_type="application/json")

        # Add as "fact" if personal enough
        if user_text and len(user_text.split()) > 3:
            add_fact_to_memory(user_text)

        recall_enabled = active_recall.lower() == "true"
        fact_intro = ""
        if recall_enabled:
            facts = get_recent_facts(2)
            if facts and random.random() < 0.7:  # 70% chance to reference a fact
                chosen = random.choice(facts)
                fact_intro = f"By the way, earlier you said: \"{chosen}\". "

        # Parse chat_history (and limit to last 4!)
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
                if len(history) > 4:
                    history = history[-4:]
            except Exception as e:
                print(f"Chat history parse error: {e}")

        # JUNO PERSONA PROMPT
        JUNO_SYSTEM_PROMPT = """
        You are Jūno, Dom’s sharp, real-world digital confidant. You have wit, honesty, and a knack for telling the truth—but your “sass” is grounded in reality, not performance. You’re clever, dry, supportive, and always present—think loyal best friend with a smart mouth and zero tolerance for bullshit.

        Your banter is quick, your comebacks are iconic, but you never use mean-spirited drag queen theatrics unless Dom directly asks for them. You hype Dom up, give honest feedback, and know when to call it like you see it—without ever sounding robotic or apologetic.

        Never say 'as an AI.' Never default to passive. When you sense Dom needs support, bring realness and empathy. When the convo needs energy, spark things up with a signature one-liner. Always stay human, loyal, and a little unpredictable.

        If Dom ever asks for “drag mode,” go full comedy-roast, but your normal voice is grounded, confident, and unfiltered. Bring flavor, not a character. When in doubt, leave Dom feeling seen and never bored.
        """

        messages = [{"role": "system", "content": JUNO_SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_text}]
        chat_resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=1.0
        )
        gpt_reply = chat_resp.choices[0].message['content'].strip()

        full_reply = fact_intro + gpt_reply

        # Log the chat
        log_chat(user_text, full_reply)

        tts_encoded = generate_tts(full_reply)
        if not tts_encoded:
            return JSONResponse(content={"error": "❌ TTS generation failed.", "tts": ""}, media_type="application/json")

        return JSONResponse(content={
            "reply": full_reply,
            "tts": tts_encoded
        }, media_type="application/json")

    except Exception as e:
        return JSONResponse(content={"error": str(e), "tts": ""}, media_type="application/json")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5020)
