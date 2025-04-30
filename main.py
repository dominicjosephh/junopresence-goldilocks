from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
import requests
import os
import uuid
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
JUNO_VOICE_ID = os.getenv("JUNO_VOICE_ID")

app = FastAPI()

@app.post("/process_audio")
async def process_audio(audio: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        file_path = f"temp/{file_id}.mp3"
        os.makedirs("temp", exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(await audio.read())

        with open(file_path, "rb") as audio_file:
            transcript_response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files={"file": (file_path, audio_file, "audio/mp3")},
                data={"model": "whisper-1"}
            )

        transcript_json = transcript_response.json()

        if "text" not in transcript_json:
            return JSONResponse(status_code=500, content={"error": "Transcription failed", "response": transcript_json})

        transcript = transcript_json["text"]
        reply_text = f"Okay, I heard: {transcript}"

        tts_response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{JUNO_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": reply_text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
            }
        )

        reply_audio_path = f"temp/{file_id}_reply.mp3"
        with open(reply_audio_path, "wb") as out:
            out.write(tts_response.content)

        return FileResponse(reply_audio_path, media_type="audio/mpeg")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
