import os
import requests
import json

TOGETHER_AI_API_KEY = os.getenv('TOGETHER_AI_API_KEY')
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"
TOGETHER_AI_TIMEOUT = 60  # adjust if you want a different timeout

def get_together_ai_reply(messages, personality="Base", max_tokens=150):
    if not TOGETHER_AI_API_KEY:
        print("No TogetherAI API key found.")
        return None
    try:
        model = "mistralai/Mistral-7B-Instruct-v0.3"
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
        print("🟢 TogetherAI PAYLOAD:", json.dumps(payload, indent=2))
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TOGETHER_AI_TIMEOUT
        )
        print("🟢 TogetherAI RAW RESPONSE:", response.text)
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and data["choices"]:
                reply = data["choices"][0]["message"]["content"].strip()
                print("🟢 TogetherAI reply:", reply)
                return reply
            else:
                print("No choices in response! Full data:", data)
                return None
        else:
            print("TogetherAI HTTP error:", response.status_code, response.text)
            return None
    except Exception as e:
        print(f"TogetherAI error: {e}")
        return None
