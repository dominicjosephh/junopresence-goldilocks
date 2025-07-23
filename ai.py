import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

def generate_elevenlabs_audio(text, voice_id=None):
    api_key = ELEVENLABS_API_KEY
    voice_id = voice_id or ELEVENLABS_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        audio_path = "static/audio/last_output.mp3"
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        with open(audio_path, "wb") as f:
            f.write(response.content)
        return f"/static/audio/last_output.mp3"
    else:
        print("❌ ElevenLabs API Error:", response.text)
        return None

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    system_message = {
        "role": "system",
        "content": (
            "You are a friendly, expressive, and emotionally-aware AI assistant. "
            "Respond to the user in a warm, vivid, and natural conversational style. "
            "If the user asks about feelings or mood, answer in a human, relatable way."
        )
    }

    if not messages or messages[0].get("role") != "system":
        messages = [system_message] + messages

    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.3",
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": max_tokens,
        "stream": False
    }
    headers = {
        "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )
        print("RAW RESPONSE TEXT:", response.text)
        response.raise_for_status()
        data = response.json()
        print("PARSED JSON:", data)

        if "choices" in data and data["choices"]:
            reply = data["choices"][0]["message"]["content"]
            print("✅ Got reply:", reply)
            audio_url = generate_elevenlabs_audio(reply) if reply else None
            return reply, audio_url
        else:
            print("[❌] No choices in response! Full data dump:", data)
            return "No valid reply from TogetherAI.", None
    except Exception as e:
        print(f"❌ Error from TogetherAI: {str(e)}")
        return f"Error from TogetherAI: {str(e)}", None
