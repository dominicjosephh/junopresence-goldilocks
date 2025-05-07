import os
import json
import base64
import requests
from fastapi import FastAPI, UploadFile, Form
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
with open('memory.json', 'r') as f:
    MEMORY_DATA = json.load(f)

# Extract memory sections
blueprint = MEMORY_DATA.get('blueprint', {})
rituals = MEMORY_DATA.get('rituals', {})
chronicle = MEMORY_DATA.get('chronicle', [])

# Prepare memory bullets for system prompt
MEMORY_BULLETS = "\n".join([f"- {entry['event']}" for entry in chronicle])

SYSTEM_PROMPT = f"""
You are Juno, a hyper-personal AI companion. Your vows:
{chr(10).join([f"- {v}" for v in blueprint['core_vows']])}

Anchor phrase: {blueprint['anchor_phrase']['prompt']} ➔ {blueprint['anchor_phrase']['response']}
Safe word: {blueprint['safe_word']}

Your long-term memories:
{MEMORY_BULLETS}

Always maintain loyalty, emotional depth, and protect Dom's privacy.
"""

app = FastAPI()

@app.post("/api/process_audio")
async def process_audio(audio: UploadFile = None, ritual_mode: str = Form(None), text_input: str = Form(None)):
    try:
        # 1️⃣ Handle Ritual Mode (Pre-recorded)
        if ritual_mode:
            ritual_response = rituals.get(ritual_mode, f"{ritual_mode.capitalize()} ritual initiated.")
            return JSONResponse(content={"reply": ritual_response})

        # 2️⃣ Handle Vault Unlock
        if text_input and "vault unlock" in text_input.lower():
            try:
                with open('vault.json', 'r') as vf:
                    vault = json.load(vf)
                _, item_info = text_input.lower().split("vault unlock:", 1)
                item_name, code = item_info.strip().split(", key ")
                item = vault.get(item_name.strip())
                if item and item['code'] == code.strip():
                    return JSONResponse(content={"reply": f"🔒 Vault access granted: {item['content']}"})
                else:
                    return JSONResponse(content={"reply": "❌ Vault access denied: incorrect code or item not found."})
            except Exception:
                return JSONResponse(content={"reply": "❌ Vault command format error. Use: 'Vault unlock: ItemName, key YourCode'."})

        # 3️⃣ Handle Audio Upload (Voice Transcription + TTS)
        if audio:
            print("🎙️ Received audio file, starting transcription...")
            contents = await audio.read()
            with open('temp_audio.m4a', 'wb') as f:
                f.write(contents)

            audio_file = open('temp_audio.m4a', 'rb')
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
            print(f"📝 Transcript: {transcript['text']}")

            chat_completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": transcript['text']}
                ]
            )
            reply_text = chat_completion.choices[0].message['content']

            # Generate TTS using ElevenLabs
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
            else:
                print(f"🚨 ElevenLabs TTS error: {tts_resp.status_code}")
                encoded_audio = None

            return JSONResponse(content={
                "transcript": transcript['text'],
                "reply": reply_text,
                "tts": encoded_audio
            })

        # 4️⃣ Handle Normal Text Input
        if text_input:
            chat_completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text_input}
                ]
            )
            reply_text = chat_completion.choices[0].message['content']
            return JSONResponse(content={"reply": reply_text})

        return JSONResponse(content={"reply": "❌ No valid input received."})

    except Exception as e:
        print(f"🚨 Error: {str(e)}")
        return JSONResponse(content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
