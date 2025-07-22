from fastapi import FastAPI
from pydantic import ValidationError
from process_audio import AudioRequest  # Adjust import as needed for your project
from ai import get_together_ai_reply  # Make sure this points to your real LLM function

app = FastAPI()

@app.post("/api/process_audio")
async def process_audio(request: AudioRequest):
    try:
        print(f"Incoming request with personality: {request.personality}")
        print(f"Incoming messages: {request.messages}")

        # --- PATCHED INPUT VALIDATION FOR DEBUGGING ---
        # If messages is missing or not a list, create a dummy message for testing
        if not isinstance(request.messages, list) or not request.messages:
            print("⚠️ messages missing or empty! Using fallback.")
            messages = [{"role": "user", "content": "Say something witty!"}]
        else:
            messages = request.messages

        # If last message is not a dict or missing 'content', fix it for debug
        last_msg = messages[-1]
        if not isinstance(last_msg, dict) or "content" not in last_msg or not last_msg["content"]:
            print("⚠️ Last message invalid, adding fallback content.")
            messages[-1] = {"role": "user", "content": "Say something clever!"}

        print("🟩 About to call get_together_ai_reply() with:", messages)
        reply = get_together_ai_reply(
            messages=messages,
            personality=request.personality,
            max_tokens=150
        )

        print("🟦 LLM reply:", reply)
        return {
            "reply": reply if isinstance(reply, str) and reply else "",
            "error": None,
            "audio_url": getattr(request, "audio_url", None),
            "music_command": getattr(request, "music_command", None),
            "truncated": 0
        }

    except (ValidationError, ValueError) as e:
        print(f"❌ Validation error in process_audio: {e}")
        return {
            "reply": "Sorry, I encountered a validation error.",
            "error": str(e),
            "audio_url": getattr(request, "audio_url", None),
            "music_command": getattr(request, "music_command", None),
            "truncated": 0
        }
    except Exception as e:
        print(f"🔥 Unexpected error in process_audio: {e}")
        return {
            "reply": "Sorry, something went wrong on the server.",
            "error": str(e),
            "audio_url": getattr(request, "audio_url", None),
            "music_command": getattr(request, "music_command", None),
            "truncated": 0
        }
