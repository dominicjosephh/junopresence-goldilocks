from speech_service import get_speech_service

# Singleton for speech-to-text (Whisper, etc.)
speech_service = get_speech_service(model_size="base")

def transcribe_audio(audio_bytes) -> str:
    result = speech_service.transcribe_audio(audio_bytes)
    return result.get("text", "")
