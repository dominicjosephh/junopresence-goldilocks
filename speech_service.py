import whisper

class SpeechService:
    def __init__(self, model_size="base"):
        self.model = whisper.load_model(model_size)

    def transcribe_audio(self, audio_bytes):
        # Save audio_bytes to a temporary file for whisper
        with open("temp.wav", "wb") as f:
            f.write(audio_bytes)
        result = self.model.transcribe("temp.wav")
        return result

# Singleton pattern
_speech_service = None
def get_speech_service(model_size="base"):
    global _speech_service
    if _speech_service is None:
        _speech_service = SpeechService(model_size=model_size)
    return _speech_service
