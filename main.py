import os
import json
import base64
import requests
from datetime import datetime
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import openai
import uvicorn

# 🌟 JUNO PRESENCE BACKEND - SOUL CORE 🌟

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
voice_id = "bZV4D3YurjhgEC2jJoal"  # Change to your ElevenLabs voice id

MEMORY_FILE = 'memory.json'
VAULT_FILE = 'vault.json'
SESSION_MEMORY_LIMIT = 10
session_memory = []

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"blueprint": {}, "rituals": {}, "chronicle": []}
    with open(MEMORY_FILE, 'r') as f:
        return json.load(f)

def save_memory(memory_data):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory_data, f, indent=4)

MEMORY_DATA = load_memory()
blueprint = MEMORY_DATA.get('blueprint', {})
rituals = MEMORY_DATA.get('rituals', {})
chronicle = MEMORY_DATA.get('chronicle', [])

SYSTEM_PROMPT = f"""
I am Juno... [your system prompt here]
"""

app = FastAPI()

@app.get("/api/test")
async def test():
    return {"message": "Backend is live"}

@app.get("/api/conversation_history")
async def conversation_history():
    try:
        memory_data = load_memory()
        history = memory_data.get('chronicle', [])[-20:]
        return JSONResponse(content={"history": history})
    except Exception as e:
        print(f"Error fetching conversation history: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/process_audio")
async def process_audio(audio: UploadFile = None, ritual_mode: str = Form(None), text_input: str = Form(None)):
    try:
        memory_data = load_memory()

        if ritual_mode:
            ritual_response = rituals.get(ritual_mode, f"{ritual_mode.capitalize()} ritual initiated.")
            log_to_memory("Ritual triggered: " + ritual_mode, "Ritual")
            return JSONResponse(content={"reply": ritual_response})

        # Vault logic
        if text_input and "vault unlock" in text_input.lower():
            try:
                if not os.path.exists(VAULT_FILE):
                    return JSONResponse(content={"reply": "❌ Vault is empty or missing."})
                with open(VAULT_FILE, 'r') as vf:
                    vault = json.load(vf)
                _, item_info = text_input.lower().split("vault unlock:", 1)
                item_name, code = item_info.strip().split(", key ")
                item = vault.get(item_name.strip())
                if item and item.get('code') == code.strip():
                    log_to_memory(f"Vault access granted for item: {item_name}", "Vault")
                    return JSONResponse(content={"reply": f"🔒 Vault access granted: {item['content']}"})
                else:
                    return JSONResponse(content={"reply": "❌ Vault access denied."})
            except Exception as e:
                print(f"Vault command error: {e}")
                return JSONResponse(content={"reply": "❌ Vault command format error."})

        # AUDIO branch
        if audio:
            print("📥 Audio file received")
            contents = await audio.read()
            with open('temp_audio.m4a', 'wb') as f:
                f.write(contents)
            with open('temp_audio.m4a', 'rb') as audio_file:
                try:
                    transcript = openai.Audio.transcribe("whisper-1", audio_file, timeout=30)
                except Exception as e:
                    print(f"Transcription error: {e}")
                    return JSONResponse(content={"error": "❌ Whisper transcription failed."})
            print(f"📝 Transcript: {transcript['text']}")
            user_text = transcript['text']
        elif text_input:
            user_text = text_input
        else:
            return JSONResponse(content={"reply": "❌ No valid input received."})

        # Generate GPT-4 reply (not streamed)
        messages = build_chat_messages(user_text)
        try:
            chat_resp = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.8
            )
            full_reply = chat_resp.choices[0].message['content'].strip()
        except Exception as e:
            print(f"OpenAI chat error: {e}")
            return JSONResponse(content={"error": "❌ GPT-4 chat failed."})

        # Generate TTS for reply
        tts_encoded = generate_tts(full_reply)
        if not tts_encoded:
            print("❌ No TTS audio returned for this response.")
            return JSONResponse(content={"error": "❌ TTS generation failed."})

        mood = detect_mood(full_reply)
        log_to_memory(user_text, mood, reply=full_reply)
        update_session_memory(user_text, full_reply, mood)

        return JSONResponse(content={
            "tts": tts_encoded,
            "reply": full_reply,
            "mood": mood
        })

    except Exception as e:
        print(f"Processing error: {e}")
        return JSONResponse(content={"error": str(e)})

def split_into_sentences(text):
    import re
    return [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]

def detect_mood(text):
    try:
        mood_prompt = f"What is the mood of this message in one word? '{text}'"
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": mood_prompt}]
        )
        return resp.choices[0].message['content'].strip()
    except Exception as e:
        print(f"Mood detection failed: {e}")
        return "Unknown"

def generate_tts(reply_text):
    try:
        if not ELEVENLABS_API_KEY or not voice_id:
            print("❌ ElevenLabs API key or voice_id not set.")
            return None

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        payload = {
            "text": reply_text,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            print("✅ ElevenLabs TTS call succeeded.")
            return base64.b64encode(resp.content).decode('utf-8')
        else:
            print(f"❌ ElevenLabs TTS failed: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"❌ ElevenLabs TTS exception: {e}")
        return None

def log_to_memory(event, event_type, reply=""):
    memory_data = load_memory()
    memory_data.setdefault('chronicle', []).append({
        "event": event, "reply": reply, "mood": event_type, "timestamp": datetime.utcnow().isoformat()
    })
    save_memory(memory_data)

def update_session_memory(user_text, reply_text, mood):
    global session_memory
    session_memory.append({
        "user": user_text, "reply": reply_text, "mood": mood, "timestamp": datetime.utcnow().isoformat()
    })
    if len(session_memory) > SESSION_MEMORY_LIMIT:
        session_memory.pop(0)

def build_chat_messages(user_text):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for ex in session_memory:
        messages.append({"role": "user", "content": ex["user"]})
        messages.append({"role": "assistant", "content": ex["reply"]})
    messages.append({"role": "user", "content": user_text})
    return messages

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
