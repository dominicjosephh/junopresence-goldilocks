import os
import json
import base64
import requests
import re
from datetime import datetime
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv
import openai
import uvicorn
import random

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
voice_id = os.getenv('ELEVENLABS_VOICE_ID')

MAX_SENTENCES = 6

app = FastAPI()

@app.get("/api/test")
async def test():
    return JSONResponse(content={"message": "Backend is live"}, media_type="application/json")

def sentence_stream(text):
    # Splits incoming GPT text into sentences as they appear.
    sentence = ''
    for char in text:
        sentence += char
        if char in '.!?':
            yield sentence.strip()
            sentence = ''
    if sentence.strip():
        yield sentence.strip()

def limit_sentences(text, max_sentences=MAX_SENTENCES):
    # Only keep the first N sentences.
    sentences = re.split(r'(?<=[.!?]) +', text)
    return ' '.join(sentences[:max_sentences])

def generate_tts(sentence):
    # Slight randomization for "human" feel
    settings = {
        "stability": 0.16 + random.uniform(-0.04, 0.04),
        "similarity_boost": 0.60 + random.uniform(-0.03, 0.03)
    }
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": sentence.strip(),
        "voice_settings": settings
    }
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode('utf-8')
    except Exception as e:
        print(f"❌ ElevenLabs TTS exception: {e}")
    return None

@app.post("/api/process_audio")
async def process_audio(audio: UploadFile = None, ritual_mode: str = Form(None), text_input: str = Form(None)):
    try:
        # --- Handle text_input or transcribe audio (as before) ---
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
        
        # --- Stream GPT response sentence by sentence ---
        def response_generator():
            gpt_stream = openai.ChatCompletion.create(
                model="gpt-4",  # Or "gpt-3.5-turbo"
                messages=[{"role": "system", "content": "Reply in a maximum of 6 sentences. Speak naturally and conversationally."},
                          {"role": "user", "content": user_text}],
                stream=True
            )
            buffer = ''
            sentences_sent = 0
            for chunk in gpt_stream:
                delta = chunk.choices[0].delta.get('content', '')
                buffer += delta
                # Send out sentences as soon as we see a delimiter.
                for sentence in list(sentence_stream(buffer)):
                    if sentence:
                        buffer = buffer[len(sentence):]
                        if sentences_sent < MAX_SENTENCES:
                            tts = generate_tts(sentence)
                            out_data = json.dumps({"reply": sentence, "tts": tts})
                            yield (out_data + '\n')
                            sentences_sent += 1
            # If there is a last partial sentence, send it.
            if buffer.strip() and sentences_sent < MAX_SENTENCES:
                tts = generate_tts(buffer.strip())
                out_data = json.dumps({"reply": buffer.strip(), "tts": tts})
                yield (out_data + '\n')

        return StreamingResponse(response_generator(), media_type="application/json")
    except Exception as e:
        return JSONResponse(content={"error": str(e), "tts": ""}, media_type="application/json")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5020)
