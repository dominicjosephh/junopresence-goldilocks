import os
import json

# ... other imports ...

def generate_reply(user_input, chat_history, personality="Base"):
    messages = []
    if chat_history:
        try:
            history = json.loads(chat_history)
            messages.extend(history)
        except Exception:
            pass
    messages.append({"role": "user", "content": user_input})

    messages_str = json.dumps(messages, sort_keys=True)
    cache_key = get_cache_key(messages_str, personality=personality)
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    max_tokens = optimize_response_length(personality, 120)

    # Try Together AI first if possible
    if TOGETHER_AI_API_KEY and (USE_TOGETHER_AI_FIRST or not os.path.exists(LLAMA_CPP_PATH)):
        together_response = get_together_ai_reply(messages, personality, max_tokens)
        if together_response:
            cache_response(cache_key, together_response)
            return together_response

    # Try local llama.cpp if available
    if os.path.exists(LLAMA_CPP_PATH) and os.path.exists(MODEL_PATH):
        local_response = get_llama3_reply(user_input, messages, personality)
        if local_response:
            cache_response(cache_key, local_response)
            return local_response

    # Fallback
    fallback = get_fallback_response(personality, user_input)
    return fallback
