import openai
import os

def generate_reply(prompt: str, history=None) -> str:
    """Generate a reply using an LLM (OpenAI, etc.)."""
    response = openai.ChatCompletion.create(
        model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        messages=[{"role": "user", "content": prompt}] + (history or [])
    )
    return response.choices[0].message["content"]
