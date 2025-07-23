import os
import json
import requests

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    # Add an emotional, expressive system prompt up front
    system_message = {
        "role": "system",
        "content": "You are a friendly, expressive, and emotionally-aware AI. Respond with warmth and natural conversation. If the user asks about feelings, tone, or emotions, reply in a vivid, human style."
    }
    # Only add if not already present
    if not messages or messages[0].get("role") != "system":
        messages = [system_message] + messages

    payload = {
        "model": "llama-3-8b-chat",
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": max_tokens
    }
    print("⚡ PAYLOAD:", json.dumps(payload, indent=2))

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
        print(f"🟪 TogetherAI STATUS: {response.status_code}")
        print("🟦 TogetherAI RAW RESPONSE:", response.text)
        response.raise_for_status()
        data = response.json()
        if "choices" in data and data["choices"]:
            print("✅ Got choices:", data["choices"])
            return data["choices"][0]["message"]["content"]
        else:
            print("❗ No choices in response!")
            return "No valid reply from TogetherAI."
    except Exception as e:
        print("🔥 Error from TogetherAI:", str(e))
        return f"Error from TogetherAI: {str(e)}"
