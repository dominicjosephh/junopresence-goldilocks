import os
from dotenv import load_dotenv
from ai_cache import (
    get_fallback_response,
    get_llama3_reply,
    get_together_ai_reply,
    optimize_response_length,
)
from utils import get_cache_key, get_cached_response, cache_response

load_dotenv()

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "together")  # fallback option

def get_models():
    return ["llama3", "together", "fallback"]

# --- Personality Handling ---

def set_personality(name: str):
    os.environ["JUNO_PERSONALITY"] = name

def get_personality() -> str:
    return os.environ.get("JUNO_PERSONALITY", "Base")

# --- Reply Generation Logic ---

def generate_reply(messages: list[dict], personality: str, model: str = DEFAULT_MODEL) -> str:
    prompt = messages[-1]["content"]
    context = messages[-2]["content"] if len(messages) > 1 else ""
    cache_key = get_cache_key(prompt, context)
    
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    if model == "llama3":
        response = get_llama3_reply(prompt, personality)
    elif model == "together":
        response = get_together_ai_reply(prompt, personality)
    else:
        response = get_fallback_response(prompt)

    response = optimize_response_length(response)
    cache_response(cache_key, response)
    return response
