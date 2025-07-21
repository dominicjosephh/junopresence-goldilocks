import os
import subprocess
import json
import logging
import requests
from utils.cache import get_cache_key, ai_cache
from utils.env import USE_TOGETHER_AI_FIRST, TOGETHER_AI_API_KEY, LLAMA_CPP_PATH, MODEL_PATH
from memory.personality import get_fallback_response
from threading import Lock
from dotenv import load_dotenv

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

TOGETHER_AI_API_KEY = os.getenv('TOGETHER_AI_API_KEY')
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"
LLAMA_CPP_PATH = "/opt/build/bin/llama-cli"
MODEL_PATH = "/opt/models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
USE_TOGETHER_AI_FIRST = os.getenv('USE_TOGETHER_AI_FIRST', 'false').lower() == 'true'
TOGETHER_AI_TIMEOUT = 15

MODEL_LOADED = False
MODEL_LOCK = Lock()
CURRENT_PERSONALITY = "Base"

RESPONSE_CACHE = {}
CACHE_MAX_SIZE = 50
CACHE_TTL = 3600  # seconds

def get_cache_key(prompt, chat_history_str="", personality="Base"):
    combined = f"{prompt}:{chat_history_str}:{personality}"
    return hashlib.md5(combined.encode()).hexdigest()

def get_cached_response(cache_key):
    if cache_key in RESPONSE_CACHE:
        response, timestamp = RESPONSE_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return response
        else:
            del RESPONSE_CACHE[cache_key]
    return None

def cache_response(cache_key, response):
    if len(RESPONSE_CACHE) >= CACHE_MAX_SIZE:
        oldest_keys = sorted(RESPONSE_CACHE.keys(), key=lambda k: RESPONSE_CACHE[k][1])[:10]
        for k in oldest_keys:
            del RESPONSE_CACHE[k]
    RESPONSE_CACHE[cache_key] = (response, time.time())

def get_fallback_response(personality="Base", user_input=""):
    fallback_responses = {
        "Sassy": [
            "Listen bestie, my brain's taking a coffee break. What's the tea though? 😏",
            "My AI is being dramatic right now, but I'm still here for the gossip! 💅",
        ],
        "Base": [
            "My response system is running a bit slow today, but I'm here. What's on your mind?",
            "Having some technical delays, but I'm still ready to chat! How can I help?",
        ],
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"❌ Together AI Exception: {e}")

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    if not TOGETHER_AI_API_KEY:
        return None
    try:
        model = model = "meta-llama/Meta-Llama-3-3B-Instruct-Turbo"
        headers = {
            "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TOGETHER_AI_TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()
            return reply
        else:
            return None
    except Exception:
        return None

def get_llama3_reply(prompt, chat_history=None, personality="Base"):
    if not os.path.exists(LLAMA_CPP_PATH) or not os.path.exists(MODEL_PATH):
        logger.warning("⚠️ LLaMA paths are invalid. Skipping local inference.")
        return None

    chat_history_str = "\n".join(chat_history) if chat_history else ""
    full_prompt = f"{chat_history_str}\n{prompt}".strip()

    try:
        cmd = [
            LLAMA_CPP_PATH,
            "-m", MODEL_PATH,
            "-p", full_prompt,
            "-n", "100"
        ]

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

        if result.returncode == 0 and result.stdout.strip():
            response = result.stdout.strip()
            if full_prompt in response:
                response = response.replace(full_prompt, "").strip()
            cache_response(cache_key, response)
            return response
    except Exception:
        pass

    fallback = get_fallback_response(personality, prompt)
    return fallback

    logger.info(f"🟢 User Input: {prompt}")
    response = None

    if USE_TOGETHER_AI_FIRST:
        logger.info("🧠 Trying Together AI...")
        formatted_messages = [{"role": "user", "content": messages_str + "\n" + prompt}]
        response = get_together_ai_reply(formatted_messages, personality)

def generate_reply(user_input, chat_history, personality="Base"):
    messages = []
    if chat_history:
        try:
            history = json.loads(chat_history)
            messages.extend(history)
        except Exception:
            pass
    messages.append({"role": "user", "content": user_input})

    if not response:
        logger.info("🧠 Falling back to Local LLaMA...")
        response = get_llama3_reply(prompt, chat_history, personality)

    if not response:
        logger.warning("🛑 All LLMs failed. Returning fallback.")
        response = get_fallback_response(personality)

    logger.info(f"🟢 Generated reply: {response}")
    ai_cache.set(cache_key, response)
    return response

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

def get_models():
    models = []
    if TOGETHER_AI_API_KEY:
        models.append("meta-llama/Llama-3-8b-chat-hf (Together AI)")
    if os.path.exists(LLAMA_CPP_PATH):
        models.append("local-llama.cpp")
    return models

def set_personality(personality):
    global CURRENT_PERSONALITY
    CURRENT_PERSONALITY = personality

def get_personality():
    return CURRENT_PERSONALITY
