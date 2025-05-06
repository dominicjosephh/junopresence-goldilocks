from fastapi import FastAPI, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import tempfile
from typing import Optional
import shutil
import base64
import requests
import openai

app = FastAPI()

# Enable CORS if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEMORY_FILE = 'memory.json'

# Ensure memory.json exists
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, 'w') as f:
        json.dump({}, f)

# Load memories into memory
def load_memories() -> dict:
    with open(MEMORY_FILE, 'r') as f:
        return json.load(f)

# Build system prompt including persona and memories
def build_system_prompt() -> str:
    memories = load_memories()
    default_persona = "You are Juno, a caring and witty companion. Always respond in clear, idiomatic English."
    if memories:
        bullets = "\n".join(f"• {k.replace('_',' ')}: {v}" for k, v in memories.items())
        return f"{default_persona}\n\nMemories:\n{bullets}"
    else:
        return default_persona

# ElevenLabs TTS
def generate_tts(text):
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
    voice_id = os.getenv('JUNO_VOICE_ID')
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY,
        'Content-Type': 'application/json'
    }
    payload = {
        'text': text,
        'model_id': 'eleven_monolingual_v1',
        'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.75
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"ElevenLabs error: {response.text}")

# Endpoint to process audio (Whisper -> GPT -> TTS)
@app.post('/api/process_audio')
async def process_audio(
    audio: bytes = File(...),
    ritual_mode: Optional[str] = Form(None)
):
    # Save incoming audio to a temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    tmp.write(audio)
    tmp.flush()
    tmp_path = tmp.name
    tmp.close()

    # 1) Transcribe
    openai.api_key = os.getenv('OPENAI_API_KEY')
    transcript_resp = openai.Audio.transcribe(
        model='whisper-1',
        file=open(tmp_path, 'rb')
    )
    transcript = transcript_resp['text']

    # 2) Build chat messages including memory
    system_msg = build_system_prompt()
    messages = [
        {'role': 'system', 'content': system_msg},
        {'role': 'user', 'content': transcript}
    ]

    # 3) Ritual mode handling
    if ritual_mode:
        file_path = f"/static/{ritual_mode}.m4a"
        os.unlink(tmp_path)
        return {'file': file_path}

    # 4) ChatGPT
    chat_resp = openai.ChatCompletion.create(
        model='gpt-4o',
        temperature=0.7,
        messages=messages
    )
    reply = chat_resp['choices'][0]['message']['content']

    # 5) TTS
    tts_binary = generate_tts(reply)
    tts_b64 = base64.b64encode(tts_binary).decode('utf-8')

    # Cleanup temp file
    os.unlink(tmp_path)

    return {
        'transcript': transcript,
        'reply': reply,
        'tts': tts_b64
    }

# Endpoint to add a memory
@app.post('/api/memory')
async def add_memory(
    key: str = Body(...),
    value: str = Body(...)
):
    memories = load_memories()
    memories[key] = value
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memories, f, indent=2)
    return {'status': 'ok', 'memory': {key: value}}
