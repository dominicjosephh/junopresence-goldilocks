import torch
from flask import Flask, request, jsonify
from transformers import pipeline, BitsAndBytesConfig
import logging

# --- FIX #2: Configure 4-bit Quantization (NECESSARY for 8GB RAM) ---
# This reduces model memory from ~16GB to ~5GB, allowing it to run.
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
)

# --- FIX #1: Load the Model Globally and ONLY ONCE ---
print("Initializing model... This may take a few minutes.")
# This pipeline object will be created once and reused for all requests.
try:
    model_pipeline = pipeline(
        "text-generation",
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        model_kwargs={
            "quantization_config": quantization_config,
        },
        device_map="auto",  # Will use CPU if no GPU is available
    )
    print("Model loaded successfully and is ready to accept requests.")
except Exception as e:
    print(f"FATAL: Failed to load the model. Error: {e}")
    # If the model fails to load, the application cannot run.
    exit()


# Initialize the Flask App
app = Flask(__name__)
# Configure logging
logging.basicConfig(level=logging.INFO)

@app.route('/generate', methods=['POST'])
def generate():
    """
    Handles text generation requests.
    Expects a JSON payload with a "prompt" key.
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            app.logger.warning("Request received without a 'prompt' field.")
            return jsonify({'error': 'JSON payload must include a "prompt" key.'}), 400

        prompt = data['prompt']
        # You can add more generation parameters here if needed
        # e.g., max_new_tokens = data.get('max_new_tokens', 256)

        app.logger.info(f"Generating text for prompt: '{prompt[:50]}...'")
        
        # Use the pre-loaded model pipeline
        outputs = model_pipeline(
            prompt,
            max_new_tokens=256,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
        )
        
        generated_text = outputs[0]['generated_text']
        app.logger.info("Successfully generated response.")

        return jsonify({'response': generated_text})

    except Exception as e:
        app.logger.error(f"An error occurred during generation: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.'}), 500

# --- FIX #3: How to Run in Production ---
# This part is for local testing. For production, use Gunicorn.
if __name__ == '__main__':
    # DO NOT use this for production.
    app.run(host='0.0.0.0', port=5000, debug=False)
