import os
import requests

# Retrieve TogetherAI API key from environment variable [oai_citation:0‡community.deeplearning.ai](https://community.deeplearning.ai/t/where-can-i-find-dlai-together-api-base/587295#:~:text=In%20the%20%E2%80%98utils,another%20environment%20variable%20called%20%E2%80%98TOGETHER_API_KEY%E2%80%99)
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
if not TOGETHER_API_KEY:
    raise RuntimeError("TOGETHER_API_KEY environment variable is not set.")

# Base URL for TogetherAI API (with default) and endpoint for chat completions
TOGETHER_API_BASE = os.getenv("TOGETHER_API_BASE", "https://api.together.xyz")
CHAT_COMPLETIONS_ENDPOINT = f"{TOGETHER_API_BASE}/v1/chat/completions"  # TogetherAI chat completion URL [oai_citation:1‡community.deeplearning.ai](https://community.deeplearning.ai/t/where-can-i-find-dlai-together-api-base/587295#:~:text=wasimsafdar%20%20October%2025%2C%202024%2C,11%3A46am%20%208)

def chat_completion(messages):
    """
    Send a chat completion request to TogetherAI's API using the specified messages.
    `messages` is a list of dicts, each with 'role' and 'content' keys.
    Returns the assistant's reply content as a string.
    """
    # Prepare request headers and payload for TogetherAI chat API
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",  # Bearer auth with API key [oai_citation:2‡community.deeplearning.ai](https://community.deeplearning.ai/t/where-can-i-find-dlai-together-api-base/587295#:~:text=In%20the%20%E2%80%98utils,another%20environment%20variable%20called%20%E2%80%98TOGETHER_API_KEY%E2%80%99)
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.3",  # Specify the model to use [oai_citation:3‡together.ai](https://www.together.ai/models/mistral-7b-instruct-v0-3#:~:text=async%20function%20main%28%29%20,%7D%5D)
        "messages": messages
    }
    # Make the POST request to TogetherAI chat completions endpoint
    response = requests.post(CHAT_COMPLETIONS_ENDPOINT, json=payload, headers=headers)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        # Provide an error message if the API call failed
        raise RuntimeError(f"Chat completion request failed: {e}") from e

    data = response.json()
    # Extract and return the assistant's reply text from the response
    return data["choices"][0]["message"]["content"]
