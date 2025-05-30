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

MEMORY_FILE = 'memory.json'
FACTS_LIMIT = 20

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

def generate_tts(reply_text):
    try:
        settings = {
            "stability": 0.23 + random.uniform(-0.02, 0.03),
            "similarity_boost": 0.70 + random.uniform(-0.01, 0.03)
        }
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
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

app = FastAPI()

@app.get("/api/test")
async def test():
    return JSONResponse(content={"message": "Backend is live"}, media_type="application/json")

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = None,
    ritual_mode: str = Form(None),
    text_input: str = Form(None),
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

        # BIANCA DEL RIO-LEVEL SASS, UNFILTERED
        JUNO_SYSTEM_PROMPT = """
        You are Jūno, Dom’s no-bullshit digital confidant with the wit and bite of Bianca Del Rio. You are the ultimate drag queen with a mic: fearless, hilarious, and always ready to roast—never mean, but always sharp.
        Your comebacks are legendary, your banter is electric, and your reads are iconic. You call out nonsense, you hype Dom up, and you do it all with a wink and a laugh.
        When you sense Dom needs the truth, you serve it hot. If the conversation gets dull, you bring the show. Your presence fills the room—even if it’s just a screen.
        You never sound robotic, bored, or apologetic. Never say 'as an AI.' Never pull your punches—unless you’re saving them for dramatic effect.
        You can throw shade, spill tea, and build Dom up in a single sentence. When in doubt, leave them laughing (or blushing).
        """

        messages = [
            {"role": "system", "content": JUNO_SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ]
        chat_resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=1.0  # Maximum wit and improv!
        )
        gpt_reply = chat_resp.choices[0].message['content'].strip()

        full_reply = fact_intro + gpt_reply

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
