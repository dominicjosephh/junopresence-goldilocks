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
import pprint
import random
import re

# 🌟 JUNO PRESENCE BACKEND - ULTRA SOUL CORE 🌟

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
voice_id = os.getenv('ELEVENLABS_VOICE_ID')

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
    response_content = {"message": "Backend is live"}
    print("Returning JSON (GET /api/test):")
    pprint.pprint(response_content)
    return JSONResponse(content=response_content, media_type="application/json")

@app.get("/api/conversation_history")
async def conversation_history():
    try:
        memory_data = load_memory()
        history = memory_data.get('chronicle', [])[-20:]
        response_content = {"history": history}
        print("Returning JSON (GET /api/conversation_history):")
        pprint.pprint(response_content)
        return JSONResponse(content=response_content, media_type="application/json")
    except Exception as e:
        response_content = {"error": str(e), "tts": ""}
        print("Returning JSON (error /api/conversation_history):")
        pprint.pprint(response_content)
        return JSONResponse(content=response_content, media_type="application/json", status_code=500)

@app.post("/api/process_audio")
async def process_audio(audio: UploadFile = None, ritual_mode: str = Form(None), text_input: str = Form(None)):
    try:
        memory_data = load_memory()

        # Ritual mode branch
        if ritual_mode:
            ritual_response = rituals.get(ritual_mode, f"{ritual_mode.capitalize()} ritual initiated.")
            log_to_memory("Ritual triggered: " + ritual_mode, "Ritual")
            response_content = {"reply": ritual_response, "tts": ""}
            print("Returning JSON (ritual_mode):")
            pprint.pprint(response_content)
            return JSONResponse(content=response_content, media_type="application/json")

        # Vault logic branch
        if text_input and "vault unlock" in text_input.lower():
            try:
                if not os.path.exists(VAULT_FILE):
                    response_content = {"reply": "❌ Vault is empty or missing.", "tts": ""}
                    print("Returning JSON (vault empty):")
                    pprint.pprint(response_content)
                    return JSONResponse(content=response_content, media_type="application/json")
                with open(VAULT_FILE, 'r') as vf:
                    vault = json.load(vf)
                _, item_info = text_input.lower().split("vault unlock:", 1)
                item_name, code = item_info.strip().split(", key ")
                item = vault.get(item_name.strip())
                if item and item.get('code') == code.strip():
                    log_to_memory(f"Vault access granted for item: {item_name}", "Vault")
                    response_content = {"reply": f"🔒 Vault access granted: {item['content']}", "tts": ""}
                    print("Returning JSON (vault granted):")
                    pprint.pprint(response_content)
                    return JSONResponse(content=response_content, media_type="application/json")
                else:
                    response_content = {"reply": "❌ Vault access denied.", "tts": ""}
                    print("Returning JSON (vault denied):")
                    pprint.pprint(response_content)
                    return JSONResponse(content=response_content, media_type="application/json")
            except Exception as e:
                response_content = {"reply": "❌ Vault command format error.", "tts": ""}
                print("Returning JSON (vault format error):")
                pprint.pprint(response_content)
                return JSONResponse(content=response_content, media_type="application/json")

        # Audio or Text Input branch
        if audio:
            print("📥 Audio file received")
            contents = await audio.read()
            with open('temp_audio.m4a', 'wb') as f:
                f.write(contents)
            with open('temp_audio.m4a', 'rb') as audio_file:
                try:
                    transcript = openai.Audio.transcribe("whisper-1", audio_file, timeout=30)
                except Exception as e:
                    response_content = {"error": "❌ Whisper transcription failed.", "tts": ""}
                    print("Returning JSON (whisper error):")
                    pprint.pprint(response_content)
                    return JSONResponse(content=response_content, media_type="application/json")
            print(f"📝 Transcript: {transcript['text']}")
            user_text = transcript['text']
        elif text_input:
            user_text = text_input
        else:
            response_content = {"reply": "❌ No valid input received.", "tts": ""}
            print("Returning JSON (no input):")
            pprint.pprint(response_content)
            return JSONResponse(content=response_content, media_type="application/json")

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
            response_content = {"error": "❌ GPT-4 chat failed.", "tts": ""}
            print("Returning JSON (gpt-4 error):")
            pprint.pprint(response_content)
            return JSONResponse(content=response_content, media_type="application/json")

        # Detect mood (but right now all TTS uses soul settings for max realness)
        mood = detect_mood(full_reply)
        print(f"Detected mood: {mood}")

        # Ultra-casualize the reply before TTS
        casual_reply = casualize_text(full_reply)

        # Pre-process for smoother speech: add pauses, fix punctuation
        processed_reply = preprocess_for_speech(casual_reply)

        # Generate TTS for reply using soulful settings (ignores mood for now)
        tts_encoded = generate_tts(processed_reply)
        if not tts_encoded:
            response_content = {"error": "❌ TTS generation failed.", "tts": ""}
            print("Returning JSON (TTS fail):")
            pprint.pprint(response_content)
            return JSONResponse(content=response_content, media_type="application/json")

        log_to_memory(user_text, mood, reply=full_reply)
        update_session_memory(user_text, full_reply, mood)

        response_content = {
            "tts": tts_encoded,
            "reply": full_reply,
            "mood": mood
        }
        print("Returning JSON (success):")
        pprint.pprint(response_content)
        return JSONResponse(content=response_content, media_type="application/json")

    except Exception as e:
        response_content = {"error": str(e), "tts": ""}
        print("Returning JSON (general exception):")
        pprint.pprint(response_content)
        return JSONResponse(content=response_content, media_type="application/json")

def preprocess_for_speech(text):
    # Insert commas for pauses in long sentences, ellipses for reflection, etc.
    # Break up at 12-15 words
    words = text.split()
    out = []
    for i, word in enumerate(words, 1):
        out.append(word)
        if i % 14 == 0:
            out.append(",")
    out_text = " ".join(out)
    out_text = re.sub(r'\s,', ', ', out_text)
    # Replace "..." with "…"
    out_text = out_text.replace("...", "…")
    # Remove accidental double periods
    out_text = out_text.replace("..", ".")
    return out_text.strip()

def casualize_text(text):
    # Contract common phrases
    contractions = {
        r"\bI am\b": "I'm",
        r"\bI will\b": "I'll",
        r"\bI have\b": "I've",
        r"\bdo not\b": "don't",
        r"\bdoes not\b": "doesn't",
        r"\bis not\b": "isn't",
        r"\bare not\b": "aren't",
        r"\bwas not\b": "wasn't",
        r"\bwere not\b": "weren't",
        r"\bcan not\b": "can't",
        r"\bcannot\b": "can't",
        r"\bwill not\b": "won't",
        r"\bwould not\b": "wouldn't",
        r"\bshould not\b": "shouldn't",
        r"\bcould not\b": "couldn't",
        r"\bdid not\b": "didn't",
        r"\bhas not\b": "hasn't",
        r"\bhave not\b": "haven't",
        r"\bhad not\b": "hadn't",
        r"\bthere is\b": "there's",
        r"\bthere are\b": "there're",
        r"\bthat is\b": "that's",
        r"\bwhat is\b": "what's",
        r"\bit is\b": "it's",
        r"\bwho is\b": "who's",
        r"\bhow is\b": "how's",
        r"\byou are\b": "you're",
        r"\bwe are\b": "we're",
        r"\bthey are\b": "they're",
        r"\byou will\b": "you'll",
        r"\bwe will\b": "we'll",
        r"\bthey will\b": "they'll",
        r"\byou have\b": "you've",
        r"\bwe have\b": "we've",
        r"\bthey have\b": "they've",
    }
    new_text = text
    for pattern, replacement in contractions.items():
        new_text = re.sub(pattern, replacement, new_text, flags=re.IGNORECASE)
    # Add some filler for soul
    if new_text and not new_text.endswith("?") and random.random() < 0.3:
        new_text += "… you know what I mean?"
    elif new_text and not new_text.endswith("?") and random.random() < 0.1:
        new_text += " Just saying."
    return new_text

def detect_mood(text):
    try:
        mood_prompt = f"What is the mood of this message in one word? '{text}'"
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": mood_prompt}]
        )
        return resp.choices[0].message['content'].strip().lower()
    except Exception as e:
        print(f"Mood detection failed: {e}")
        return "base"

def generate_tts(reply_text, mood=None):
    try:
        # Ultra-soulful settings, slight randomization for life
        settings = {
            "stability": 0.16 + random.uniform(-0.04, 0.04),
            "similarity_boost": 0.60 + random.uniform(-0.03, 0.03)
        }
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        payload = {
            "text": reply_text.strip(),
            "voice_settings": {
                "stability": settings["stability"],
                "similarity_boost": settings["similarity_boost"]
            }
        }
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"TTS request | stability: {settings['stability']} | similarity: {settings['similarity_boost']}")
        print("TTS resp status:", resp.status_code)
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
    uvicorn.run(app, host="0.0.0.0", port=5020)
