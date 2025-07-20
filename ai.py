
import os
import json
import random
import hashlib
import time
import subprocess
import requests
from threading import Lock
from dotenv import load_dotenv

load_dotenv()

TOGETHER_AI_API_KEY = os.getenv('TOGETHER_AI_API_KEY')
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"
LLAMA_CPP_PATH = "/opt/build/bin/llama-cli"
MODEL_PATH = "/opt/models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
USE_TOGETHER_AI_FIRST = os.getenv('USE_TOGETHER_AI_FIRST', 'false').lower() == 'true'
TOGETHER_AI_TIMEOUT = 15

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
        ]
    }
    responses = fallback_responses.get(personality, fallback_responses["Base"])
    return random.choice(responses)

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    if not TOGETHER_AI_API_KEY:
        print("❌ TOGETHER_AI_API_KEY not set.")
        return None
    try:
        model = "meta-llama/Meta-Llama-3-8B-Instruct"
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
            print(f"❌ Together AI returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Together AI Exception: {e}")
    return None

def get_llama3_reply(prompt, chat_history=None, personality="Base"):
    chat_history_str = str(chat_history) if chat_history else ""
    cache_key = get_cache_key(prompt, chat_history_str, personality)
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    full_prompt = prompt
    if chat_history:
        chat_history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history])
        full_prompt = f"{chat_history_text}\nUser: {prompt}"

    try:
        if not os.path.exists(LLAMA_CPP_PATH):
            print("⚠️ LLaMA executable not found.")
            return None
        if not os.path.exists(MODEL_PATH):
            print("⚠️ LLaMA model file not found.")
            return None

        cmd = [
            LLAMA_CPP_PATH,
            "-m", MODEL_PATH,
            "-p", full_prompt,
            "-n", "100"
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20, encoding='utf-8'
        )
        if result.returncode == 0 and result.stdout.strip():
            response = result.stdout.strip()
            if full_prompt in response:
                response = response.replace(full_prompt, "").strip()
            cache_response(cache_key, response)
            return response
        else:
            print(f"⚠️ LLaMA returned non-zero exit or no output.")
    except Exception as e:
        print(f"❌ LLaMA Exception: {e}")

    return None

def optimize_response_length(personality, base_length=100):
    length_modifiers = {
        "Sassy": 80,
        "Hype": 90,
        "Shadow": 85,
        "Assert": 75,
        "Challenger": 85,
        "Ritual": 120,
        "Joy": 95,
        "Empathy": 110,
    }
    return length_modifiers.get(personality, base_length)

def generate_reply(user_input, chat_history, personality="Base"):
    messages = []
    if chat_history:
        try:
            history = json.loads(chat_history)
            messages.extend(history)
        except Exception as e:
            print(f"⚠️ Failed to parse chat history: {e}")
    messages.append({"role": "user", "content": user_input})

    messages_str = json.dumps(messages, sort_keys=True)
    cache_key = get_cache_key(messages_str, personality=personality)
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    max_tokens = optimize_response_length(personality, 120)

    if TOGETHER_AI_API_KEY and (USE_TOGETHER_AI_FIRST or not os.path.exists(LLAMA_CPP_PATH)):
        response = get_together_ai_reply(messages, personality, max_tokens)
        if response:
            cache_response(cache_key, response)
            return response

    response = get_llama3_reply(user_input, messages, personality)
    if response:
        cache_response(cache_key, response)
        return response

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
