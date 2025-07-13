import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ELEVENLABS_API = os.getenv("ELEVENLABS_API")
VOICE_ID = os.getenv("VOICE_ID")
# Add more config as needed
