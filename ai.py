import whisper
import chat  # Import the chat module for sending requests to TogetherAI

# Load the Whisper model globally to avoid re-loading it on each request.
# Using the base Whisper model (for English) by default; adjust model size if needed.
_whisper_model = whisper.load_model("base")

def transcribe_with_whisper(audio_path: str) -> str:
    """
    Transcribe speech from an audio file using OpenAI's Whisper model.
    :param audio_path: Path to the audio file to transcribe.
    :return: Transcribed text from the audio.
    """
    # Use the Whisper model to transcribe the audio file
    result = _whisper_model.transcribe(audio_path)
    return result.get("text", "")  # Return the text part of the transcription result

def generate_reply(user_message: str, context_messages: list = None) -> str:
    """
    Generate a reply from the AI model given a user message.
    Optionally include context_messages (list of {'role': ..., 'content': ...} dicts)
    to provide conversation history or system prompts.
    :param user_message: The latest user input as text.
    :param context_messages: (Optional) List of previous messages (with roles) for context.
    :return: The assistant's reply text.
    """
    if context_messages is None:
        context_messages = []
    # Assemble the conversation messages, including any prior context and the new user message
    messages = list(context_messages)  # copy to avoid modifying the original list
    messages.append({"role": "user", "content": user_message})
    # Use TogetherAI chat completion API to get the assistant's reply
    reply_text = chat.chat_completion(messages)
    return reply_text
