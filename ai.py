import os
import json
import requests

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    """
    Calls TogetherAI LLM and returns only reply text (never binary).
    """
    system_message = {
        "role": "system",
        "content": (
            "You are a friendly, expressive, and emotionally-aware AI assistant. "
            "Respond to the user in a vivid, relatable, natural style. "
            "If the user asks about feelings or mood, answer in a human, relatable way."
        )
    }
    if not messages or messages[0].get("role") == "system":
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
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        # Safely parse the reply (never include non-utf8 data)
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        else:
            return "Sorry, I couldn't generate a response."
    except Exception as e:
        print("Error from TogetherAI:", str(e))
        return f"Error from TogetherAI: {str(e)}"
