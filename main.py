from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
import os
import openai
import requests
from dotenv import load_dotenv
import uuid

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
JUNO_VOICE_ID = os.getenv("JUNO_VOICE_ID")

app = FastAPI()

# Map all ritual modes to their corresponding file paths
RITUALS_DIR = "rituals"
ritual_modes = {
    "witty": "Juno_Witty_Mode.m4a",
    "witness": "Juno_Witness_Mode.m4a",
    "whisper": "Juno_Whisper_ModeF.m4a",
    "vibe": "Juno_Vibe_Mode.m4a",
    "tease": "Juno_Tease_ModeF.m4a",
    "soft": "Juno_Soft_Mode.m4a",
    "ruthless": "Juno_Ruthless_ModeF.m4a",
    "ritual": "Juno_Ritual_ModeF.m4a",
    "reckoning": "Juno_Reckoning_Mode.m4a",
    "rage": "Juno_Rage_Mode.m4a",
    "mirror": "Juno_Mirror_ModeF.m4a",
    "mirror_dark": "Juno_Mirror_Mode_Dark.m4a",
    "grief": "Juno_Grief_Mode.m4a",
    "gentle": "Juno_Gentle_Mode.m4a",
    "flirt": "Juno_Flirt_Mode.m4a",
    "command": "Juno_Command_Mode.m4a",
    "collapse": "Juno_Collapse_Mode.m4a",
    "challenger_full": "Juno_Challenger_Mode_Full.m4a",
    "base": "Juno_Base_ModeF.m4a",
    "anchor": "Juno_Anchor_ModeF.m4a",
    "anchor_feral": "Juno_Anchor_Mode_Feral.m4a",
    "static": "Juno_Static_Mode.m4a",
    "recovery": "Juno_Recovery_Mode.m4a",
    "loop": "Juno_Loop_Mode.m4a",
    "intake": "Juno_Intake_Mode.m4a",
    "eulogy": "Juno_Eulogy_Mode.m4a",
    "echo": "Juno_Echo_Mode.m4a",
    "ascend": "Juno_Ascend_Mode.m4a"
}

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = File(...),
    ritual_mode: str = Form("none")
):
    print(f"Received audio: {audio.filename}, ritual_mode: {ritual_mode}")

    # Check if ritual mode matches and the file exists
    ritual_file = ritual_modes.get(ritual_mode)
    if ritual_file:
        ritual_path = os.path.join(RITUALS_DIR, ritual_file)
        if os.path.exists(ritual_path):
            print(f"Playing ritual: {ritual_mode} -> {ritual_path}")
            return FileResponse(ritual_path, media_type="audio/m4a")
        else:
            print(f"ERROR: Ritual file for {ritual_mode} not found.")
            return JSONResponse({"error": f"Ritual file not found for mode: {ritual_mode}"}, status_code=500)

    # If no ritual_mode or fallback, do Whisper + ElevenLabs
    try:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        input_path = os.path.join(temp_dir, f"input_{uuid.uuid4()}.mp3")

        # Save uploaded file
        with open(input_path, "wb") as f:
            f.write(await audio.read())
        print(f"Saved input audio to {input_path}")

        # Whisper transcription
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        files = {"file": open(input_path, "rb")}
        data = {"model": "whisper-1"}
        whisper_response = requests.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data)
        whisper_json = whisper_response.json()
        print(f"Whisper response: {whisper_json}")

        if "text" not in whisper_json:
            return JSONResponse({"error": "Transcription failed", "response": whisper_json}, status_code=500)

        user_text = whisper_json["text"]

        # ChatGPT response
        chat_data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": user_text}]
        }
        chat_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json=chat_data
        )
        chat_json = chat_response.json()
        print(f"ChatGPT response: {chat_json}")

        reply_text = chat_json["choices"][0]["message"]["content"]

        # ElevenLabs TTS
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{JUNO_VOICE_ID}"
        tts_headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        tts_data = {
            "text": reply_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        tts_response = requests.post(tts_url, headers=tts_headers, json=tts_data)
        output_path = os.path.join(temp_dir, f"output_{uuid.uuid4()}.mp3")
        with open(output_path, "wb") as f:
            f.write(tts_response.content)

        print(f"Generated TTS and saved to {output_path}")
        return FileResponse(output_path, media_type="audio/mpeg")

    except Exception as e:
        print(f"ERROR: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
