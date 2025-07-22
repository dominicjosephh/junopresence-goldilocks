import os
import json
import random
import hashlib
import time
import requests
from .ai_cache import get_cache_key, get_cached_response, cache_response

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

def generate_chat_response(messages):
    print("🚦 Entered generate_chat_response()")
    cache_key = get_cache_key(messages)
    print(f"🗝️ cache_key: {cache_key}")
    cached = get_cached_response(cache_key)
    if cached:
        print("💾 Returning cached response!")
        return cached

    headers = {
        "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-7b-instruct-v0.1",
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 250
    }

    print(f"📤 Sending payload to TogetherAI: {json.dumps(payload, indent=2)}")
    response = requests.post(
        f"{TOGETHER_AI_BASE_URL}/chat/completions",
        headers=headers,
        json=payload
    )

    try:
        print(f"🔵 TogetherAI status: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        print("🟢 Raw TogetherAI response:", json.dumps(result, indent=2))
        reply = result["choices"][0]["message"]["content"]
        print(f"🟡 Extracted reply: {reply}")
        cache_response(cache_key, reply)
        return reply
    except Exception as e:
        print("🔥 LLM request failed:", e)
        print("🧾 Response text:", response.text)
        return "Sorry, I had trouble generating a response."
