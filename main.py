from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
from ai import get_together_ai_reply, transcribe_with_whisper

load_dotenv()

app = FastAPI()

# Allow CORS for your frontend (modify origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        personality = data.get("personality", "Base")
        reply = get_together_ai_reply(messages, personality)
        return JSONResponse(content={"reply": reply, "error": None})
    except Exception as e:
        return JSONResponse(
            content={"reply": None, "error": f"Server error: {str(e)}"},
            status_code=500
        )

@app.post("/api/whisper")
async def whisper_endpoint(request: Request):
    # Example for future use, right now just a stub
    try:
        # You would normally get a file here
        return JSONResponse(content={"transcript": "Not implemented."})
    except Exception as e:
        return JSONResponse(content={"transcript": None, "error": str(e)}, status_code=500)

@app.get("/")
async def root():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5020, reload=True)
