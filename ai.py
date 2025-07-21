
from ai_cache import get_fallback_response, get_llama3_reply, optimize_response_length

def generate_reply(messages, personality, max_tokens=150):
    # Ensure messages is a list of dicts
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    elif isinstance(messages, list):
        messages = [m for m in messages if isinstance(m, dict) and "content" in m]

    try:
        prompt = messages[-1]["content"]
    except (IndexError, TypeError):
        return {
            "reply": "[Error] Invalid message format.",
            "audio_url": None,
            "truncated": 0,
            "error": "Missing or malformed messages",
            "music_commands": []
        }

    # Default mock system prompt (can be extended for different personalities)
    system_prompt = f"You are a helpful assistant with the personality: {personality}"

    conversation = [{"role": "system", "content": system_prompt}, *messages]

    try:
        # Choose backend model logic (replace or expand as needed)
        response_text = get_llama3_reply(conversation, personality=personality, max_tokens=max_tokens)

        return {
            "reply": response_text,
            "audio_url": None,
            "truncated": 0,
            "error": None,
            "music_commands": []
        }

    except Exception as e:
        fallback = get_fallback_response(messages)
        return {
            "reply": fallback,
            "audio_url": None,
            "truncated": 1,
            "error": str(e),
            "music_commands": []
        }
