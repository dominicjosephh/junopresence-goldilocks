from fastapi import FastAPI, WebSocket
from speech import transcribe_audio
from ai import generate_reply
from memory import store_memory, retrieve_memory
from music import handle_music_command
from tts import synthesize_speech

app = FastAPI()

@app.websocket("/ws/convo")
async def websocket_convo(websocket: WebSocket):
    await websocket.accept()
    while True:
        audio_bytes = await websocket.receive_bytes()
        user_text = transcribe_audio(audio_bytes)
        reply = generate_reply(user_text)
        tts_audio = synthesize_speech(reply)
        await websocket.send_bytes(tts_audio)

@app.post("/api/music")
async def music_endpoint(command: str):
    result = handle_music_command(command)
    return {"result": result}

@app.post("/api/memory")
async def memory_endpoint(key: str, value: str):
    store_memory(key, value)
    return {"status": "ok"}
