import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import openai
import requests
import tempfile
import uuid

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-xxx")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "eleven-xxx")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "your-voice-id")
WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"  # Or your own if self-hosted

openai.api_key = OPENAI_API_KEY

# --- ENDPOINTS ---

@app.route("/api/test", methods=["GET"])
def test():
    return jsonify({"status": "Juno backend live"})

@app.route("/api/process_audio", methods=["POST"])
def process_audio():
    # Receive audio file
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400
    audio_file = request.files["audio"]
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
        audio_path = temp.name
        audio_file.save(audio_path)

    # Whisper STT
    with open(audio_path, "rb") as f:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        data = {"model": "whisper-1", "language": "en"}
        files = {"file": f}
        response = requests.post(WHISPER_API_URL, headers=headers, data=data, files=files)
        transcription = response.json().get("text", "")

    if not transcription:
        os.remove(audio_path)
        return jsonify({"error": "Transcription failed"}), 500

    # OpenAI GPT-4/3.5 Chat Completion
    chat_prompt = f"You are Juno, a supportive, expressive AI assistant. Respond naturally and helpfully.\nUser: {transcription}\nJuno:"
    gpt_response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are Juno, a supportive, expressive AI assistant."},
            {"role": "user", "content": transcription},
        ],
        max_tokens=256,
        temperature=0.8,
    )
    reply = gpt_response.choices[0].message.content.strip()

    # ElevenLabs TTS
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    tts_headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    tts_data = {
        "text": reply,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }
    tts_response = requests.post(tts_url, headers=tts_headers, json=tts_data)
    if tts_response.status_code != 200:
        os.remove(audio_path)
        return jsonify({"error": "TTS failed"}), 500

    # Save TTS audio file
    output_audio_path = f"/tmp/{uuid.uuid4()}.mp3"
    with open(output_audio_path, "wb") as out_f:
        out_f.write(tts_response.content)

    os.remove(audio_path)
    return send_file(output_audio_path, mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=False)
