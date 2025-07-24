import os
import requests
import json

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

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
        "max_tokens": max_tokens
    }

    print("PAYLOAD:", json.dumps(payload, indent=2))
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
            print("✅ Got choices:", data["choices"])
            return data["choices"][0]["message"]["content"]
        else:
            print("❗️No choices in response! Full data dump:", data)
            return "No valid reply from TogetherAI."
    except Exception as e:
        print("❌ Error from TogetherAI:", str(e))
        return f"Error from TogetherAI: {str(e)}"

# ---------- ELEVENLABS TTS ----------
def generate_tts_audio(text, output_dir):
    """
    Replace this stub with your ElevenLabs TTS logic.
    """
    print(f"🔊 [TTS] Would generate audio for: {text} in {output_dir}")
    # Actual implementation here
    return f"{output_dir}/dummy_audio.mp3"

# ---------- WHISPER TRANSCRIPTION ----------
def transcribe_with_whisper(audio_path_or_bytes):
    """
    Replace this stub with your Whisper ASR logic.
    Accepts audio file path or bytes.
    """
    print(f"📝 [Whisper] Would transcribe: {audio_path_or_bytes}")
    # Actual implementation here
    return "Transcription not implemented."
