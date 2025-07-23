import os
import tempfile
import requests
from dotenv import load_dotenv
import utf8_validation
import logging

logger = logging.getLogger(__name__)

load_dotenv()

WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
USE_LOCAL_WHISPER = os.getenv("USE_LOCAL_WHISPER", "false").lower() == "true"

def transcribe_audio(audio_bytes):
    """
    Transcribes audio bytes to text using either OpenAI Whisper API or local whisper.cpp.
    Returns UTF-8 safe text only.
    """
    if not audio_bytes:
        return "No audio data provided."
    
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
            
            # Read output file with explicit UTF-8 encoding
            txt_path = audio_path.replace(".wav", ".txt")
            try:
                with open(txt_path, "r", encoding='utf-8') as txt_file:
                    transcription = txt_file.read().strip()
            except UnicodeDecodeError:
                # Fallback to reading with error handling
                with open(txt_path, "r", encoding='utf-8', errors='replace') as txt_file:
                    transcription = txt_file.read().strip()
            
            # Clean up files
            try:
                os.remove(audio_path)
                os.remove(txt_path)
            except OSError:
                pass  # Files may not exist
            
            # Ensure UTF-8 safety
            transcription = utf8_validation.sanitize_text(transcription)
            logger.info(f"Local STT transcription: {transcription[:100]}...")
            return transcription
            
        except subprocess.TimeoutExpired:
            logger.error("Local whisper timeout")
            return "Audio transcription timed out."
        except Exception as e:
            utf8_validation.log_encoding_issue("local_stt", None, e)
            return "Local STT processing error."

    # Default: Use OpenAI Whisper API (or any compatible API)
    if not WHISPER_API_KEY:
        return "Speech-to-text service not configured."
        
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
            result = response.json()
            transcription = result.get("text", "")
            
            # Ensure UTF-8 safety
            if not utf8_validation.is_valid_utf8(transcription):
                utf8_validation.log_encoding_issue("whisper_api_transcription", transcription)
                transcription = utf8_validation.sanitize_text(transcription)
            
            transcription = utf8_validation.sanitize_text(transcription)
            logger.info(f"Whisper API transcription: {transcription[:100]}...")
            return transcription
        else:
            error_msg = f"Whisper API error: {response.status_code}"
            logger.error(error_msg)
            return "Speech recognition service error."
            
    except requests.exceptions.RequestException as e:
        utf8_validation.log_encoding_issue("whisper_api_request", None, e)
        logger.error(f"Whisper API request error: {e}")
        return "Speech recognition connection error."
    except Exception as e:
        utf8_validation.log_encoding_issue("whisper_api_general", None, e)
        logger.error(f"STT error: {e}")
        return "Speech recognition error."
