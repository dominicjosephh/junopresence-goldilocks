import requests
import os

ELEVENLABS_API = os.getenv("ELEVENLABS_API", "")
VOICE_ID = os.getenv("VOICE_ID", "")

def synthesize_speech(text: str) -> bytes:
    """Synthesize speech using ElevenLabs API (example)."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API}
    response = requests.post(url, json={"text": text}, headers=headers)
    return response.content
