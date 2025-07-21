import os
import subprocess
import json
import logging
import requests
from utils import get_cache_key, get_cached_response, cache_responsefrom utils.env 
import USE_TOGETHER_AI_FIRST, TOGETHER_AI_API_KEY, LLAMA_CPP_PATH, MODEL_PATH
from memory.personality import get_fallback_response

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
        return None

def get_llama3_reply(prompt, chat_history=None, personality="Base"):
    if not os.path.exists(LLAMA_CPP_PATH) or not os.path.exists(MODEL_PATH):
        logger.warning("⚠️ LLaMA paths are invalid. Skipping local inference.")
        return None

    chat_history_str = "\n".join(chat_history) if chat_history else ""
    full_prompt = f"{chat_history_str}\n{prompt}".strip()

    try:
        result = subprocess.run(
            [LLAMA_CPP_PATH, "-m", MODEL_PATH, "-p", full_prompt, "-n", "100"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
        if result.returncode != 0:
            logger.error(f"⚠️ LLaMA returned non-zero exit: {result.stderr.decode()}")
            return None
        output = result.stdout.decode().strip()
        return output
    except subprocess.TimeoutExpired:
        logger.error("❌ LLaMA inference timed out.")
        return None
    except Exception as e:
        logger.error(f"❌ LLaMA Exception: {e}")
        return None

def generate_reply(prompt, chat_history=None, personality="Base"):
    messages_str = "\n".join(chat_history) if chat_history else ""
    cache_key = get_cache_key(prompt, messages_str, personality)
    cached_response = ai_cache.get(cache_key)
    if cached_response:
        logger.info("⚡ Using cached response.")
        return cached_response

    logger.info(f"🟢 User Input: {prompt}")
    response = None

    if USE_TOGETHER_AI_FIRST:
        logger.info("🧠 Trying Together AI...")
        formatted_messages = [{"role": "user", "content": messages_str + "\n" + prompt}]
        response = get_together_ai_reply(formatted_messages, personality)

    if not response:
        logger.info("🧠 Falling back to Local LLaMA...")
        response = get_llama3_reply(prompt, chat_history, personality)

    if not response:
        logger.warning("🛑 All LLMs failed. Returning fallback.")
        response = get_fallback_response(personality)

    logger.info(f"🟢 Generated reply: {response}")
    ai_cache.set(cache_key, response)
    return response
