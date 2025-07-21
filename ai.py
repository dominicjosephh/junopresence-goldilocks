from ai_cache import get_cache_key, get_cached_response, cache_response
from utils import get_together_ai_reply, optimize_response_length
import os
import openai

def generate_reply(messages, personality="Base", max_tokens=150):
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")
    if not isinstance(messages[-1], dict) or "content" not in messages[-1]:
        raise ValueError("Last message must be a dict with a 'content' key")

    prompt = messages[-1]["content"]
    cache_key = get_cache_key(prompt, personality)

    cached = get_cached_response(cache_key)
    if cached:
        return cached

    print(f"Calling AI with personality={personality}, max_tokens={max_tokens}")
    response = get_together_ai_reply(messages, personality, max_tokens)
    
    # Ensure we always return a string - if AI API fails, use fallback
    if response is None:
        from utils import get_fallback_response
        response = get_fallback_response(personality, prompt)
    
    optimized_response = optimize_response_length(response)

    cache_response(cache_key, optimized_response)
    return optimized_response
