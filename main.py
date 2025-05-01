import os
import uuid
import shutil
import logging
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
JUNO_VOICE_ID = os.getenv("JUNO_VOICE_ID")

# Setup folders
TEMP_DIR = "temp"
RITUALS_DIR = "rituals"
LOGS_DIR = "logs"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "juno.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Initialize FastAPI
app = FastAPI()

# Placeholder whisper + GPT processing (to be filled with actual logic)
def transcribe_audio(audio_path: str) -> str:
    logging.info(f"Transcribing audio: {audio_path}")
    return "Hello, I am Juno."  # Mocked result

def generate_response(text: str) -> str:
    logging.info(f"Generating response to: {text}")
    return f"You said: {text}"  # Mocked GPT reply

def generate_voice_elevenlabs(text: str, output_path: str):
    logging.info(f"Generating voice using ElevenLabs...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{JUNO_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        logging.info("Voice generation complete.")
    else:
        logging.error(f"Failed to generate voice: {response.status_code} {response.text}")
        raise Exception("Voice generation failed.")

# API route
@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = File(...),
    ritual_mode: str = Form(default="none")
):
    try:
        # Save uploaded file
        temp_filename = f"{uuid.uuid4()}.mp3"
        temp_path = os.path.join(TEMP_DIR, temp_filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        # Check ritual mode
        if ritual_mode != "none":
            ritual_file = os.path.join(RITUALS_DIR, f"{ritual_mode}.m4a")
            if os.path.exists(ritual_file):
                logging.info(f"Playing ritual mode: {ritual_mode}")
                return FileResponse(ritual_file, media_type="audio/x-m4a")
            else:
                logging.warning(f"Ritual mode '{ritual_mode}' not found.")

        # Otherwise: transcribe, respond, and speak
        transcript = transcribe_audio(temp_path)
        reply = generate_response(transcript)

        # Save generated voice
        output_path = os.path.join(TEMP_DIR, f"response_{uuid.uuid4()}.mp3")
        generate_voice_elevenlabs(reply, output_path)

        logging.info(f"Reply sent successfully. Transcript: {transcript}")
        return FileResponse(output_path, media_type="audio/mpeg")

    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        try:
            audio.file.close()
        except:
            pass
