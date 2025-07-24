import os
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "IKWqu6ade5yIfCYnvKwr")
ELEVENLABS_TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

def generate_tts_audio(text):
    # Generate a hash of the text for unique filenames (avoid duplicates)
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    audio_file_path = f"static/tts_{text_hash}.mp3"
    audio_url = f"/static/tts_{text_hash}.mp3"

    # If file already exists, don't re-generate
    if os.path.exists(audio_file_path):
        return audio_url

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }

    try:
        response = requests.post(ELEVENLABS_TTS_URL, headers=headers, json=payload)
        response.raise_for_status()
        with open(audio_file_path, "wb") as f:
            f.write(response.content)
        return audio_url
    except Exception as e:
        print("❌ ElevenLabs TTS error:", e)
        return None
