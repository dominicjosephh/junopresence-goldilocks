import os
import uuid
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
JUNO_VOICE_ID = os.getenv("JUNO_VOICE_ID")

app = FastAPI()

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = File(...),
    ritual_mode: str = Form("none")
):
    print(f"[INFO] Received audio file: {audio.filename}")
    print(f"[INFO] Ritual mode: {ritual_mode}")

    # Handle ritual mode first
    if ritual_mode and ritual_mode.lower() != "none":
        ritual_file = f"rituals/Juno_{ritual_mode.capitalize()}_Mode.m4a"
        if os.path.exists(ritual_file):
            print(f"[RITUAL] Serving ritual audio file: {ritual_file}")
            return FileResponse(ritual_file, media_type="audio/x-m4a")
        else:
            print(f"[RITUAL] Ritual file not found: {ritual_file}")
            return JSONResponse(
                content={"error": f"Ritual file not found: {ritual_file}"},
                status_code=404
            )

    # Save uploaded file temporarily (unique name)
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    unique_id = uuid.uuid4().hex
    temp_input_path = os.path.join(temp_dir, f"input_{unique_id}.mp3")
    with open(temp_input_path, "wb") as f:
        f.write(await audio.read())
    print(f"[INFO] Saved uploaded file to: {temp_input_path}")

    # Transcribe with OpenAI Whisper
    try:
        print("[INFO] Starting transcription with Whisper API...")
        with open(temp_input_path, "rb") as f:
            transcript_response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files={"file": (audio.filename, f, audio.content_type)},
                data={"model": "whisper-1"}
            )
        transcript_response.raise_for_status()
        transcript_data = transcript_response.json()
        text = transcript_data.get("text", "").strip()
        print(f"[INFO] Transcription result: {text}")
    except Exception as e:
        print(f"[ERROR] Transcription failed: {e}")
        return JSONResponse(content={"error": "Transcription failed"})

    # Generate a reply (for demo: echo back the transcript)
    reply_text = f"You said: {text}"
    print(f"[INFO] Reply text to synthesize: {reply_text}")

    # Use ElevenLabs to synthesize the reply
    try:
        print("[INFO] Starting ElevenLabs TTS generation...")
        tts_response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{JUNO_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": reply_text,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
        )
        tts_response.raise_for_status()
    except Exception as e:
        print(f"[ERROR] ElevenLabs TTS failed: {e}")
        return JSONResponse(content={"error": "TTS generation failed"})

    # Check if ElevenLabs returned actual audio
    if "audio/mpeg" not in tts_response.headers.get("Content-Type", ""):
        print(f"[ERROR] ElevenLabs did not return audio. Response: {tts_response.text}")
        return JSONResponse(content={"error": "TTS generation failed (invalid audio response)"})

    # Save synthesized audio (unique filename)
    output_path = os.path.join(temp_dir, f"reply_{unique_id}.mp3")
    with open(output_path, "wb") as out:
        out.write(tts_response.content)

    print(f"[INFO] Reply audio saved to: {output_path} (size: {len(tts_response.content)} bytes)")

    return FileResponse(output_path, media_type="audio/mpeg")
