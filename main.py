from fastapi import FastAPI, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import tempfile
from typing import Optional
import shutil

from openai import OpenAI

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
    openai = OpenAI()
    transcript_resp = openai.audio.transcriptions.create(
        file=open(tmp_path, 'rb'),
        model='whisper-1'
    )
    transcript = transcript_resp.text

    # 2) Build chat messages including memory
    system_msg = build_system_prompt()
    messages = [
        {'role': 'system', 'content': system_msg},
        {'role': 'user', 'content': transcript}
    ]

    # 3) If this is a ritual request
    if ritual_mode:
        # Directly return the ritual file path
        # Assuming static files served under /static/...
        file_path = f"/static/{ritual_mode}.m4a"
        return {'file': file_path}

    # 4) ChatGPT
    chat_resp = openai.chat.completions.create(
        model='gpt-4o-mini',
        temperature=0.7,
        messages=messages
    )
    reply = chat_resp.choices[0].message.content

    # 5) TTS
    tts_resp = openai.audio.speech.create(
        file=reply,
        model_id='eleven_monolingual_v1',
        voice_id=os.getenv('JUNO_VOICE_ID')
    )
    tts_binary = tts_resp.audio
    tts_b64 = tts_binary.decode('base64')  # pseudo-code

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
