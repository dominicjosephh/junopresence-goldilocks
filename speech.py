import os
import tempfile
import requests
from dotenv import load_dotenv

load_dotenv()

WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
USE_LOCAL_WHISPER = os.getenv("USE_LOCAL_WHISPER", "false").lower() == "true"

def transcribe_audio(audio_bytes):
    """
    Transcribes audio bytes to text using either OpenAI Whisper API or local whisper.cpp.
    """
    if USE_LOCAL_WHISPER:
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                audio_path = f.name
            
            # Call local whisper.cpp (assume `whisper` CLI in PATH)
            import subprocess
            cmd = ["whisper", audio_path, "--model", "base.en", "--output_format", "txt", "--language", "en"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # Read output file
            txt_path = audio_path.replace(".wav", ".txt")
            with open(txt_path, "r") as txt_file:
                transcription = txt_file.read().strip()
            os.remove(audio_path)
            os.remove(txt_path)
            return transcription
        except Exception as e:
            return f"Local STT error: {e}"

    # Default: Use OpenAI Whisper API (or any compatible API)
    if not WHISPER_API_KEY:
        return "No Whisper API key set."
    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={
                "Authorization": f"Bearer {WHISPER_API_KEY}"
            },
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": "whisper-1", "language": "en"},
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get("text", "")
        else:
            return f"Whisper API error: {response.text}"
    except Exception as e:
        return f"STT error: {e}"
