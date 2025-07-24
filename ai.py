import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()  # This will read your .env file!

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    system_message = {
        "role": "system",
        "content": (
            f"You are a friendly, expressive, and emotionally-aware AI assistant. "
            f"Respond in a warm, vivid, natural conversational style. "
            f"Your personality is: {personality}."
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

    headers = {
        "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        else:
            return "No valid reply from TogetherAI."
    except Exception as e:
        print("❌ Error from TogetherAI:", str(e))
        return f"Error from TogetherAI: {str(e)}"

def transcribe_with_whisper(audio_path):
    print(f"[Whisper] Would transcribe file: {audio_path}")
    return "Transcription not implemented."
