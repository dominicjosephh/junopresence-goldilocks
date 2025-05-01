import os
import uuid
import shutil
import logging
import requests
import openai
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
JUNO_VOICE_ID = os.getenv("JUNO_VOICE_ID")

openai.api_key = OPENAI_API_KEY

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

def transcribe_audio_whisper(audio_path: str) -> str:
    logging.info(f"Transcribing audio with Whisper API: {audio_path}")
    with open(audio_path, "rb") as audio_file:
        response = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file
        )
    transcript = response.get("text", "")
    logging.info(f"Transcription result: {transcript}")
    return transcript

def generate_gpt_response(prompt: str) -> str:
    logging.info(f"Generating GPT response for prompt: {prompt}")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are Juno, a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    reply = response["choices"][0]["message"]["content"].strip()
    logging.info(f"GPT reply: {reply}")
    return reply

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

        # Transcribe with Whisper + respond with GPT
        transcript = transcribe_audio_whisper(temp_path)
        reply = generate_gpt_response(transcript)

        # Generate ElevenLabs voice
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
