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
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data.get("response")
        except Exception as e:
            print(f"Cache read error: {e}")
    return None

def cache_response(cache_key: str, response: str):
    path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    try:
        with open(path, "w") as f:
            json.dump({"response": response}, f)
    except Exception as e:
        print(f"Cache write error: {e}")

def get_fallback_response(prompt: str, context: str = "") -> str:
    return "Sorry, something went wrong. Please try again later."

def get_llama3_reply(prompt: str, context: str = "") -> str:
    return f"[LLAMA3 response to]: {prompt}"

def get_together_ai_reply(prompt: str, context: str = "") -> str:
    return f"[Together.AI response to]: {prompt}"

def optimize_response_length(text: str, max_tokens: int = 500) -> str:
    words = text.split()
    if len(words) <= max_tokens:
        return text
    return " ".join(words[:max_tokens]) + "..."
