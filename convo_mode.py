from fastapi import UploadFile, File
from ai import transcribe_with_whisper, get_together_ai_reply  # see below for helper

@app.post("/api/convo_mode")
async def convo_mode(audio: UploadFile = File(...)):
    try:
        # Save uploaded audio file
        audio_path = "static/audio/user_input.wav"
        with open(audio_path, "wb") as f:
            f.write(await audio.read())
        
        # Transcribe audio (Whisper STT)
        transcript = transcribe_with_whisper(audio_path)
        print("User transcript:", transcript)

        # LLM reply + ElevenLabs voice
        messages = [{"role": "user", "content": transcript}]
        reply, audio_url = get_together_ai_reply(messages=messages, personality="Base", max_tokens=150)

        return {
            "reply": reply if isinstance(reply, str) and reply else "",
            "transcript": transcript,
            "audio_url": audio_url,
            "error": None
        }
    except Exception as e:
        print("❌ Error in convo_mode:", e)
        return {
            "reply": "",
            "transcript": "",
            "audio_url": None,
            "error": str(e)
        }
