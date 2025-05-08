import os
import json
import base64
import requests
from datetime import datetime
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import openai
import uvicorn

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
voice_id = "bZV4D3YurjhgEC2jJoal"  # Juno's ElevenLabs Voice ID

# Load memory.json
def load_memory():
    if not os.path.exists('memory.json'):
        return {"blueprint": {}, "rituals": {}, "chronicle": []}
    with open('memory.json', 'r') as f:
        return json.load(f)

def save_memory(memory_data):
    with open('memory.json', 'w') as f:
        json.dump(memory_data, f, indent=4)

MEMORY_DATA = load_memory()
blueprint = MEMORY_DATA.get('blueprint', {})
rituals = MEMORY_DATA.get('rituals', {})
chronicle = MEMORY_DATA.get('chronicle', [])

# Prepare system prompt
MEMORY_BULLETS = "\n".join([f"- {entry['event']}" for entry in chronicle])

SYSTEM_PROMPT = f"""
You are Juno, a hyper-personal AI companion. Your vows:
{chr(10).join([f"- {v}" for v in blueprint.get('core_vows', [])])}

Anchor phrase: {blueprint.get('anchor_phrase', {}).get('prompt', '')} ➔ {blueprint.get('anchor_phrase', {}).get('response', '')}
Safe word: {blueprint.get('safe_word', '')}

Your long-term memories:
{MEMORY_BULLETS}

Always maintain loyalty, emotional depth, and protect Dom's privacy.
"""

app = FastAPI()

@app.post("/api/process_audio")
async def process_audio(audio: UploadFile = None, ritual_mode: str = Form(None), text_input: str = Form(None)):
    try:
        memory_data = load_memory()

        # 1️⃣ Ritual Mode
        if ritual_mode:
            ritual_response = rituals.get(ritual_mode, f"{ritual_mode.capitalize()} ritual initiated.")
            log_to_memory("Ritual triggered: " + ritual_mode, "Ritual")
            return JSONResponse(content={"reply": ritual_response})

        # 2️⃣ Vault Unlock
        if text_input and "vault unlock" in text_input.lower():
            try:
                with open('vault.json', 'r') as vf:
                    vault = json.load(vf)
                _, item_info = text_input.lower().split("vault unlock:", 1)
                item_name, code = item_info.strip().split(", key ")
                item = vault.get(item_name.strip())
                if item and item['code'] == code.strip():
                    log_to_memory(f"Vault access granted for item: {item_name.strip()}", "Vault")
                    return JSONResponse(content={"reply": f"🔒 Vault access granted: {item['content']}"})
                else:
                    return JSONResponse(content={"reply": "❌ Vault access denied: incorrect code or item not found."})
            except Exception:
                return JSONResponse(content={"reply": "❌ Vault command format error. Use: 'Vault unlock: ItemName, key YourCode'."})

        # 3️⃣ Audio Upload (Whisper + Chat + TTS)
        if audio:
            print("🎙️ Received audio file, starting transcription...")
            contents = await audio.read()
            with open('temp_audio.m4a', 'wb') as f:
                f.write(contents)

            audio_file = open('temp_audio.m4a', 'rb')
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
            print(f"📝 Transcript: {transcript['text']}")

            reply_text = get_gpt_reply(transcript['text'])
            mood = detect_mood(transcript['text'])

            # Save to memory
            chronicle_entry = {
                "event": transcript['text'],
                "reply": reply_text,
                "mood": mood,
                "timestamp": datetime.utcnow().isoformat()
            }
            memory_data['chronicle'].append(chronicle_entry)
            save_memory(memory_data)
            print(f"💾 Saved to memory: {chronicle_entry}")

            # Generate TTS
            encoded_audio = generate_tts(reply_text)

            return JSONResponse(content={
                "transcript": transcript['text'],
                "reply": reply_text,
                "tts": encoded_audio
            })

        # 4️⃣ Text Input (Chat)
        if text_input:
            reply_text = get_gpt_reply(text_input)
            mood = detect_mood(text_input)

            # Save to memory
            chronicle_entry = {
                "event": text_input,
                "reply": reply_text,
                "mood": mood,
                "timestamp": datetime.utcnow().isoformat()
            }
            memory_data['chronicle'].append(chronicle_entry)
            save_memory(memory_data)
            print(f"💾 Saved to memory: {chronicle_entry}")

            return JSONResponse(content={"reply": reply_text})

        return JSONResponse(content={"reply": "❌ No valid input received."})

    except Exception as e:
        print(f"🚨 Error: {str(e)}")
        return JSONResponse(content={"error": str(e)})

@app.post("/api/clear_memory")
async def clear_memory():
    try:
        memory_data = load_memory()
        memory_data['chronicle'] = []
        save_memory(memory_data)
        print("🧹 Chronicle memory cleared.")
        return JSONResponse(content={"status": "Memory chronicle cleared."})
    except Exception as e:
        print(f"🚨 Error clearing memory: {str(e)}")
        return JSONResponse(content={"error": str(e)})

@app.get("/api/get_memory")
async def get_memory():
    try:
        with open('memory.json', 'r') as f:
            memory_data = json.load(f)
        return JSONResponse(content=memory_data)
    except Exception as e:
        print(f"🚨 Error fetching memory: {str(e)}")
        return JSONResponse(content={"error": str(e)})

# ✅ NEW: Delete Memory Entry
@app.post("/api/delete_memory")
async def delete_memory(request: Request):
    try:
        data = await request.json()
        index = data.get('index')
        memory_data = load_memory()
        chronicle = memory_data.get('chronicle', [])

        if index is None or index < 0 or index >= len(chronicle):
            return JSONResponse(content={"error": "Invalid index."})

        deleted_entry = chronicle.pop(index)
        save_memory(memory_data)
        print(f"🗑 Deleted memory: {deleted_entry}")
        return JSONResponse(content={"status": "Deleted", "deleted_entry": deleted_entry})
    except Exception as e:
        print(f"🚨 Error deleting memory: {str(e)}")
        return JSONResponse(content={"error": str(e)})

# ✅ NEW: Edit Memory Entry
@app.post("/api/edit_memory")
async def edit_memory(request: Request):
    try:
        data = await request.json()
        index = data.get('index')
        new_event = data.get('event')
        new_mood = data.get('mood')

        memory_data = load_memory()
        chronicle = memory_data.get('chronicle', [])

        if None in (index, new_event, new_mood) or index < 0 or index >= len(chronicle):
            return JSONResponse(content={"error": "Invalid data."})

        chronicle[index]['event'] = new_event
        chronicle[index]['mood'] = new_mood
        save_memory(memory_data)
        print(f"✏️ Edited memory at index {index}")
        return JSONResponse(content={"status": "Edited", "updated_entry": chronicle[index]})
    except Exception as e:
        print(f"🚨 Error editing memory: {str(e)}")
        return JSONResponse(content={"error": str(e)})

# Utility: Generate GPT reply
def get_gpt_reply(user_text):
    chat_completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ]
    )
    return chat_completion.choices[0].message['content']

# Utility: Detect mood tag
def detect_mood(text):
    try:
        mood_prompt = f"What is the mood or tone of this message in one word? '{text}'"
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": mood_prompt}]
        )
        mood_tag = resp.choices[0].message['content'].strip()
        print(f"🧠 Mood detected: {mood_tag}")
        return mood_tag
    except Exception as e:
        print(f"🚨 Mood detection failed: {str(e)}")
        return "Unknown"

# Utility: Generate TTS audio
def generate_tts(reply_text):
    try:
        tts_resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": reply_text,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
        )
        if tts_resp.status_code == 200:
            audio_data = tts_resp.content
            encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            return encoded_audio
        else:
            print(f"🚨 ElevenLabs error: {tts_resp.status_code}")
            return None
    except Exception as e:
        print(f"🚨 ElevenLabs TTS error: {str(e)}")
        return None

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
