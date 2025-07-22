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
    cache_key = get_cache_key(messages)
    cached = get_cached_response(cache_key)
    if cached:
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

    response = requests.post(
        f"{TOGETHER_AI_BASE_URL}/chat/completions",
        headers=headers,
        json=payload
    )

    try:
        response.raise_for_status()
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        cache_response(cache_key, reply)
        return reply
    except Exception as e:
        print("🔥 LLM request failed:", e)
        print("🧾 Response text:", response.text)
        return "Sorry, I had trouble generating a response."

