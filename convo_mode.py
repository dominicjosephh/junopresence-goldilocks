from fastapi import APIRouter, UploadFile, File, Form
from ai import transcribe_with_whisper

convo_router = APIRouter()

@convo_router.post("/api/convo_mode")
async def convo_mode_endpoint(
    audio: UploadFile = File(...),
    personality: str = Form("Base")
):
    audio_bytes = await audio.read()
    transcription = transcribe_with_whisper(audio_bytes)
    # You could now send this transcription to your LLM or handle logic as needed.
    return {"reply": transcription or "(No reply generated)"}
