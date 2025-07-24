from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from ai import transcribe_with_whisper
import tempfile
import os

convo_router = APIRouter()

@convo_router.post("/api/convo_mode")
async def convo_mode_endpoint(
    audio: UploadFile = File(...),
    personality: str = Form("Base")
):
    try:
        # Save audio to a temp file
        suffix = os.path.splitext(audio.filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Transcribe the saved file
        transcription = transcribe_with_whisper(tmp_path)

        # Clean up temp file
        os.remove(tmp_path)

        return JSONResponse(content={
            "reply": transcription or "(No reply generated)"
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process audio: {e}"}
        )
