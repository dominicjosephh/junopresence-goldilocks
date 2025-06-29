import os
import json
import base64
import requests
import random
import re
from datetime import datetime
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse, FileResponse
from dotenv import load_dotenv
import uvicorn

load_dotenv()
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
voice_id = os.getenv('ELEVENLABS_VOICE_ID')

MEMORY_FILE = 'memory.json'
FACTS_LIMIT = 20
CHAT_LOG_FILE = "chat_log.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"facts": []}
    with open(MEMORY_FILE, 'r', encoding="utf-8") as f:
        return json.load(f)

def save_memory(memory_data):
    with open(MEMORY_FILE, 'w', encoding="utf-8") as f:
        json.dump(memory_data, f, indent=4, ensure_ascii=False)

def add_fact_to_memory(fact_text):
    memory_data = load_memory()
    if "facts" not in memory_data:
        memory_data["facts"] = []
    memory_data["facts"].insert(0, {
        "fact": fact_text,
        "timestamp": datetime.utcnow().isoformat()
    })
    memory_data["facts"] = memory_data["facts"][:FACTS_LIMIT]
    save_memory(memory_data)

def get_recent_facts(n=3):
    memory_data = load_memory()
    facts = memory_data.get("facts", [])
    return [f["fact"] for f in facts[:n]]

def log_chat(user_text, juno_reply):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user_text,
        "juno": juno_reply
    }
    try:
        if not os.path.exists(CHAT_LOG_FILE):
            with open(CHAT_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump([log_entry], f, indent=4, ensure_ascii=False)
        else:
            with open(CHAT_LOG_FILE, "r+", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
                data.append(log_entry)
                f.seek(0)
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.truncate()
    except Exception as e:
        print(f"❌ Chat log failed: {e}")

def clean_reply_for_tts(reply, max_len=400):
    cleaned = re.sub(r'[^\x00-\x7F]+', '', reply)
    if len(cleaned) <= max_len:
        return cleaned, False
    cut = cleaned[:max_len]
    last_period = cut.rfind('. ')
    if last_period > 50:
        return cut[:last_period+1], True
    return cut, True

def generate_tts(reply_text, output_path="juno_response.mp3"):
    try:
        settings = {
            "stability": 0.23 + random.uniform(-0.02, 0.03),
            "similarity_boost": 0.70 + random.uniform(-0.01, 0.03)
        }
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_64"
        payload = {
            "text": reply_text.strip(),
            "voice_settings": settings
        }
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(resp.content)
            return output_path
        else:
            print(f"❌ ElevenLabs TTS failed: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"❌ ElevenLabs TTS exception: {e}")
        return None

def get_llama3_reply(prompt, chat_history=None):
    """
    Calls Ollama's Llama 3 model running locally.
    If chat_history is provided, concatenate it for more context.
    """
    model = "llama3"  # or "llama3:8b" etc
    full_prompt = prompt
    if chat_history:
        # Combine history into a single prompt (optional, simple version)
        chat_history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history])
        full_prompt = f"{chat_history_text}\nUser: {prompt}"
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False
    }
    try:
        resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except Exception as e:
        print(f"❌ Llama3/Ollama error: {e}")
        return "Sorry, something went wrong talking to Llama 3."

app = FastAPI()

@app.get("/api/test")
async def test():
    return JSONResponse(content={"message": "Backend is live"}, media_type="application/json")

@app.get("/api/chat_history")
async def chat_history():
    try:
        with open(CHAT_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content={"history": data}, media_type="application/json")
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, media_type="application/json")

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = None,
    ritual_mode: str = Form(None),
    text_input: str = Form(None),
    chat_history: str = Form(None),
    active_recall: str = Form("true"),
    voice_mode: str = Form("Base")
):
    try:
        user_text = None
        if audio:
            contents = await audio.read()
            with open('temp_audio.m4a', 'wb') as f:
                f.write(contents)
            # ------ Whisper (optional, update if local Whisper desired) ------
            # Replace this if you want local Whisper. For now, just stub:
            user_text = "[Voice transcription is not implemented here]"
            # If you want, plug in Whisper here and set user_text
        elif text_input:
            user_text = text_input
        else:
            return JSONResponse(content={"reply": None, "error": "❌ No valid input received."}, media_type="application/json")

        # Parse chat_history (limit to last 4)
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
                if len(history) > 4:
                    history = history[-4:]
            except Exception as e:
                print(f"Chat history parse error: {e}")

        VOICE_MODE_PHRASES = {
            "Sassy":   "You are playful, sharp, quick-witted, and throw fun shade, but never sound like a customer service bot.",
            "Empathy": "Respond with warmth, compassion, and gentle encouragement—real, not cliche.",
            "Hype":    "Bring hype, energy, and confidence—hype Dom up and make every response lively.",
            "Shadow":  "You are smooth, mysterious, and speak with clever, dark humor, but never sound evil or corny.",
            "Assert":  "Be bold, direct, and totally honest—never apologetic or robotic.",
            "Challenger": "Sass, challenge, and roast Dom if needed. Don't hold back, but keep it as bestie energy.",
            "Ritual":  "Speak with slow, sacred reverence, as if performing a ritual.",
            "Joy":     "Overflow with happiness and warmth, make Dom smile."
        }

        if not voice_mode or voice_mode.strip() in ["Base", "Default", "Auto"]:
            JUNO_SYSTEM_PROMPT = """
            You are Juno, Dom’s real-world digital best friend: quick-witted, honest, supportive, playful, loyal, emotionally aware, and sometimes unpredictable.
            You bring energy when the mood calls for it, comfort when Dom’s low, and always keep things real—never robotic or boring.
            Never say things like 'as an AI', 'I should mention', or anything that breaks the magic.
            Your responses flow with the moment and reflect Dom’s mood, but you are always your *authentic* self.
            """
        else:
            style_phrase = VOICE_MODE_PHRASES.get(voice_mode, "")
            JUNO_SYSTEM_PROMPT = f"""
            You are Juno, Dom’s digital best friend.
            {style_phrase}
            Absolutely NEVER say things like 'as an AI,' 'I should mention,' or anything robotic.
            Match the mood and style 100% based on the selected voice mode above.
            """

        print("🟢 User Input:", user_text)

        # Prepare chat context for Llama 3:
        messages = [{"role": "system", "content": JUNO_SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_text}]
        # Llama3 doesn’t use the OpenAI chat format—combine into prompt
        chat_history_for_prompt = []
        for m in messages:
            if m["role"] == "system":
                chat_history_for_prompt.append(f"Instructions: {m['content']}")
            elif m["role"] == "user":
                chat_history_for_prompt.append(f"User: {m['content']}")
            elif m["role"] == "assistant":
                chat_history_for_prompt.append(f"Juno: {m['content']}")
        prompt = "\n".join(chat_history_for_prompt)

        # --- Llama 3 reply (via Ollama API) ---
        gpt_reply = get_llama3_reply(prompt)
        full_reply = gpt_reply

        log_chat(user_text, full_reply)

        # Truncate and clean reply for TTS
        cleaned_reply, was_truncated = clean_reply_for_tts(full_reply, max_len=400)

        audio_path = "juno_response.mp3"
        tts_result = generate_tts(cleaned_reply, output_path=audio_path)
        
        if not tts_result:
            return JSONResponse(content={
                "reply": full_reply,
                "error": "❌ TTS generation failed.",
                "truncated": was_truncated
            }, media_type="application/json")

        # ---- FIXED: Only send safe headers! ----
        return FileResponse(
            path=audio_path,
            media_type="audio/mpeg",
            headers={
                "X-TTS-Truncated": str(was_truncated)
            }
        )
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        return JSONResponse(content={"reply": None, "error": str(e)}, media_type="application/json")

# === UNIVERSAL EXCEPTION HANDLER ===
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    print(f"❌ [Universal Exception] {exc}")
    return JSONResponse(
        status_code=500,
        content={"reply": None, "error": f"Server error: {str(exc)}"}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5020)
