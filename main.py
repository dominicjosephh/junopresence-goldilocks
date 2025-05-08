from flask import Flask, request, jsonify
import json
import os
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

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

# 🚀 ROUTE: Get full memory (for vault + export)
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

# ✅ OPTIONAL: Example route to save a new memory (used by your AI flow)
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

# ✅ ROOT TEST (optional)
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'message': 'Juno backend is alive!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
