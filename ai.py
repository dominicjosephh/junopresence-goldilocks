import os
import requests
import hashlib
import json

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

def get_llm_reply(message, personality="Base"):
    # Change to your TogetherAI details/model as needed
    url = "https://api.together.xyz/v1/chat/completions"
    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.3",
        "messages": [
            {"role": "user", "content": message}
        ]
    }
    headers = {
        "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    if "choices" in data and data["choices"]:
        return data["choices"][0]["message"]["content"]
    else:
        return "Sorry, I couldn't get a reply."

def generate_tts(text, output_dir):
    # Use ElevenLabs API
    voice_id = ELEVENLABS_VOICE_ID or "default"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1"
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    audio_content = response.content

    # Make filename deterministic by hash (so no collisions)
    audio_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    filename = f"{audio_hash}.mp3"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "wb") as f:
        f.write(audio_content)
    return filename
