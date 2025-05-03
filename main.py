# main.py
import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

app = FastAPI()

def run_whisper_transcription(file_path: str) -> str:
    """
    Replace this stub with your actual Whisper transcription logic.
    For example:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        return result["text"]
    """
    # TODO: implement transcription
    return "transcription not yet implemented"

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = File(...),
    ritual_mode: Optional[str] = Form(None)
):
    # Serve a pre-recorded ritual if requested
    if ritual_mode:
        ritual_file = f"rituals/Juno_{ritual_mode.capitalize()}_Mode.m4a"
        if os.path.exists(ritual_file):
            return JSONResponse(
                status_code=200,
                content={"ritual_mode": ritual_mode, "file": ritual_file}
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"error": f"Ritual '{ritual_mode}' not found"}
            )

    # Otherwise, save the upload to temp and transcribe
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, audio.filename)
    with open(file_path, "wb") as f:
        f.write(await audio.read())

    try:
        transcript = run_whisper_transcription(file_path)
    except Exception as e:
        # Clean up and return an error
        os.remove(file_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Transcription failed: {str(e)}"}
        )

    # Clean up the temporary file
    os.remove(file_path)

    # Return the transcript as JSON
    return JSONResponse(status_code=200, content={"transcript": transcript})
