import os
import tempfile
from fastapi import APIRouter, File, UploadFile, HTTPException
from ai import transcribe_with_whisper, generate_reply

router = APIRouter()

@router.post("/convo_mode")
async def conversation_mode(file: UploadFile = File(...)):
    """
    API endpoint to handle conversation mode with audio input.
    - Expects an audio file upload (user's speech).
    - Transcribes the audio using Whisper.
    - Generates an AI response using the transcribed text.
    Returns JSON with both the transcription and the AI reply.
    """
    if not file:
        # This case should be handled by FastAPI automatically when File(...) is required
        raise HTTPException(status_code=400, detail="No audio file provided.")
    # Read the uploaded file's content into memory
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read the uploaded file: {e}")

    # Write the file to a temporary location so Whisper can access it
    temp_audio_path = None
    try:
        # Preserve the original file extension if available for Whisper/ffmpeg compatibility
        ext = ""
        if file.filename:
            _, ext = os.path.splitext(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(contents)
            tmp.flush()
            temp_audio_path = tmp.name
        # Transcribe the audio file to text
        transcription = transcribe_with_whisper(temp_audio_path)
    except Exception as e:
        # Handle errors in the transcription process
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {e}")
    finally:
        # Clean up the temporary file
        if temp_audio_path:
            try:
                os.remove(temp_audio_path)
            except OSError:
                pass

    if not transcription:
        # If Whisper didn't return any text (e.g., silent audio or error), handle it as an error
        raise HTTPException(status_code=500, detail="Transcription was empty or failed.")

    # Use the transcribed text to get an AI-generated reply
    try:
        reply_text = generate_reply(transcription)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI reply generation failed: {e}")

    # Return the results as JSON
    return {"transcription": transcription, "reply": reply_text}
