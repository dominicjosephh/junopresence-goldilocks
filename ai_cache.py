import os
import json
import hashlib

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_key(prompt: str, context: str = "") -> str:
    hash_input = f"{prompt}:{context}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

def get_cached_response(cache_key: str) -> str | None:
    path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
            return data.get("response")
    return None

def cache_response(cache_key: str, response: str):
    path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    with open(path, "w") as f:
        json.dump({"response": response}, f)

def get_fallback_response(prompt: str, context: str = "") -> str:
    return "Sorry, something went wrong. Please try again later."
