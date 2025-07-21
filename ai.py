import os
import subprocess
import json
import logging
import requests
from utils import (
    get_cache_key,
    get_cached_response,
    cache_response,
    USE_TOGETHER_AI_FIRST,
    TOGETHER_AI_API_KEY,
    LLAMA_CPP_PATH,
    MODEL_PATH,
    get_fallback_response
)

logger = logging.getLogger(__name__)

def get_together_ai_reply(messages, personality):
    model = "meta-llama/Llama-3-8b-chat-hf"
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"❌ Together AI Exception: {e}")
        return get_fallback_response(personality, messages[-1]["content"])
