from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
import openai
import requests
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# 🔑 ENV VARIABLES
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_KEY_HERE')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', 'YOUR_11LABS_KEY_HERE')
VOICE_ID = 'bZV4D3YurjhgEC2jJoal'

openai.api_key = OPENAI_API_KEY

MEMORY_FILE = 'memory.json'

# ✅ Helper: Load memory
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {'chronicle': []}
    with open(MEMORY_FILE, 'r') as f:
        return json.load(f)

# ✅ Helper: Save memory
def save_memory(data):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# 🚀 ROUTE: Process Audio (transcribe + reply)
@app.route('/api/process_audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio = request.files['audio']
    filename = secure_filename(audio.filename)

    with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
        audio.save(tmp.name)
        audio_path = tmp.name

    try:
        # 1️⃣ Transcribe using Whisper
        audio_file = open(audio_path, "rb")
        transcript_data = openai.Audio.transcribe("whisper-1", audio_file)
        transcript = transcript_data['text']
        print(f"Transcript: {transcript}")

        # 2️⃣ Generate reply using GPT
        prompt = f"You are Juno. The user said: '{transcript}'. How do you respond?"
        chat_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Juno, an AI assistant."},
                {"role": "user", "content": transcript}
            ]
        )
        reply_text = chat_response['choices'][0]['message']['content'].strip()
        print(f"Reply: {reply_text}")

        # 3️⃣ Synthesize audio using ElevenLabs
        tts_resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": reply_text,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
        )

        if tts_resp.status_code != 200:
            print("Error from ElevenLabs:", tts_resp.text)
            return jsonify({
                'transcript': transcript,
                'reply': reply_text,
                'tts': None
            })

        tts_base64 = tts_resp.content.encode("base64").decode('utf-8')

        # 4️⃣ Save memory
        memory = load_memory()
        chronicle = memory.get('chronicle', [])
        chronicle.append({
            'event': transcript,
            'reply': reply_text,
            'mood': 'neutral',
            'timestamp': datetime.utcnow().isoformat()
        })
        save_memory({'chronicle': chronicle})

        return jsonify({
            'transcript': transcript,
            'reply': reply_text,
            'tts': tts_base64
        })

    except Exception as e:
        print("Error processing audio:", str(e))
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

# 🚀 ROUTE: Get full memory (Vault + Export)
@app.route('/api/get_memory', methods=['GET'])
def get_memory():
    memory = load_memory()
    return jsonify(memory)

# 🚀 ROUTE: Delete memory entry
@app.route('/api/delete_memory', methods=['POST'])
def delete_memory():
    data = request.get_json()
    index = data.get('index')
    if index is None:
        return jsonify({'error': 'Missing index'}), 400

    memory = load_memory()
    chronicle = memory.get('chronicle', [])

    if index < 0 or index >= len(chronicle):
        return jsonify({'error': 'Invalid index'}), 400

    deleted = chronicle.pop(index)
    save_memory({'chronicle': chronicle})
    return jsonify({'status': 'deleted', 'deleted_entry': deleted, 'chronicle': chronicle})

# 🚀 ROUTE: Edit memory entry
@app.route('/api/edit_memory', methods=['POST'])
def edit_memory():
    data = request.get_json()
    index = data.get('index')
    new_event = data.get('event')
    new_mood = data.get('mood')

    if None in (index, new_event, new_mood):
        return jsonify({'error': 'Missing fields'}), 400

    memory = load_memory()
    chronicle = memory.get('chronicle', [])

    if index < 0 or index >= len(chronicle):
        return jsonify({'error': 'Invalid index'}), 400

    chronicle[index]['event'] = new_event
    chronicle[index]['mood'] = new_mood
    save_memory({'chronicle': chronicle})
    return jsonify({'status': 'edited', 'updated_entry': chronicle[index], 'chronicle': chronicle})

# 🚀 ROUTE: Save new memory entry manually
@app.route('/api/save_memory', methods=['POST'])
def save_new_memory():
    data = request.get_json()
    event = data.get('event')
    reply = data.get('reply')
    mood = data.get('mood', 'neutral')
    timestamp = datetime.utcnow().isoformat()

    if not event or not reply:
        return jsonify({'error': 'Missing event or reply'}), 400

    memory = load_memory()
    chronicle = memory.get('chronicle', [])
    chronicle.append({
        'event': event,
        'reply': reply,
        'mood': mood,
        'timestamp': timestamp
    })
    save_memory({'chronicle': chronicle})
    return jsonify({'status': 'saved', 'chronicle': chronicle})

# ✅ ROUTE: Test
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'message': 'Juno backend is alive!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
