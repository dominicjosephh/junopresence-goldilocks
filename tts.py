import os
import requests
from dotenv import load_dotenv
import tempfile

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice

def synthesize_speech(text):
    """
    Synthesizes speech from text using ElevenLabs API.
    Returns: bytes of MP3 audio.
    """
    if not ELEVENLABS_API_KEY:
        return b""

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.7
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.content  # MP3 bytes
        else:
            print(f"TTS error: {response.text}")
            return b""
    except Exception as e:
        print(f"TTS exception: {e}")
        return b""

# Optionally, add a mock/local TTS fallback:
def synthesize_speech_local(text):
    """
    Fallback: Synthesizes speech using a local TTS engine (espeak, etc.).
    Returns: bytes of WAV audio.
    """
    try:
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        subprocess.run(["espeak", text, "-w", wav_path], check=True)
        with open(wav_path, "rb") as wav:
            audio_bytes = wav.read()
        os.remove(wav_path)
        return audio_bytes
    except Exception as e:
        print(f"Local TTS error: {e}")
        return b""
