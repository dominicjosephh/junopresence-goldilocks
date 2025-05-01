import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import openai

load_dotenv()

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# ROUTE: Root check
@app.get("/")
def root():
    return {"message": "Juno Presence backend is running."}

# ROUTE: Process audio
@app.post("/api/process_audio")
async def process_audio(audio: UploadFile = File(...), ritual_mode: str = Form("none")):
    print(f"[RITUAL] Received request with ritual_mode: {ritual_mode}")

    if ritual_mode and ritual_mode.lower() != "none":
        ritual_file_path = f"rituals/Juno_{ritual_mode.capitalize()}_Mode.m4a"
        if os.path.exists(ritual_file_path):
            print(f"[RITUAL] Serving ritual audio file: {ritual_file_path}")
            return FileResponse(ritual_file_path, media_type="audio/x-m4a")
        else:
            print(f"[RITUAL] Ritual mode '{ritual_mode}' not found or file missing.")
            return JSONResponse(content={"error": "Ritual file not found"}, status_code=404)

    # If no ritual mode, process via Whisper (default behavior)
    try:
        print("[PROCESS] No ritual_mode or set to 'none'; transcribing with Whisper.")
        # Save uploaded file temporarily
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, audio.filename)
        with open(temp_file_path, "wb") as f:
            f.write(await audio.read())

        # Whisper transcription (OpenAI)
        print(f"[TRANSCRIBE] Sending file to Whisper: {temp_file_path}")
        transcript = openai.Audio.transcribe("whisper-1", open(temp_file_path, "rb"))
        text = transcript["text"]
        print(f"[TRANSCRIBE] Transcription result: {text}")

        return JSONResponse(content={"text": text})

    except Exception as e:
        print(f"[ERROR] Exception during transcription: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
