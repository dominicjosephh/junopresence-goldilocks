from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
import os
import uuid
from ai import get_together_ai_reply, transcribe_with_whisper, generate_tts_audio 
from convo_mode import router as convo_mode_router

app.include_router(convo_mode_router)
router = APIRouter()

AUDIO_OUTPUT_DIR = "audio_output"
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

@router.post("/api/convo_mode")
async def convo_mode(
    audio: UploadFile = File(...),
    personality: str = Form("Base"),
    messages: Optional[str] = Form(None),  # JSON-encoded string, if used
    spotify_access_token: Optional[str] = Form(None)
):
    try:
        # Save uploaded audio
        audio_ext = audio.filename.split(".")[-1]
        audio_filename = f"{uuid.uuid4()}.{audio_ext}"
        audio_path = os.path.join(AUDIO_OUTPUT_DIR, audio_filename)
        with open(audio_path, "wb") as f:
            f.write(await audio.read())

        # Transcribe audio (plug in your Whisper or OpenAI code here)
        transcript = transcribe_with_whisper(audio_path)
        print("User transcript:", transcript)

        # Parse recent messages if provided
        msg_list = []
        if messages:
            import json
            try:
                msg_list = json.loads(messages)
            except Exception as e:
                print("Could not parse messages:", e)
        
        # Call LLM to get reply
        all_messages = msg_list + [{"role": "user", "content": transcript}]
        reply = get_together_ai_reply(all_messages, personality=personality, max_tokens=150)

        # Generate TTS audio (returns local filename or url)
        reply_audio_filename = generate_tts_audio(reply, AUDIO_OUTPUT_DIR)
        reply_audio_url = f"/api/audio/{reply_audio_filename}"

        # (Optional) Use the spotify_access_token if needed, e.g. for music search

        return JSONResponse({
            "reply": reply,
            "audio_url": reply_audio_url,
            "error": None
        })

    except Exception as e:
        print(f"❌ Error in convo_mode: {e}")
        return JSONResponse(
            {"reply": "", "audio_url": None, "error": str(e)},
            status_code=500
        )
