@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = None,
    ritual_mode: str = Form(None),
    text_input: str = Form(None),
    chat_history: str = Form(None),
    active_recall: str = Form("true"),
    voice_mode: str = Form("Base")  # <--- this is the voice mode sent from iOS
):
    try:
        user_text = None
        # Transcribe or accept text input
        if audio:
            contents = await audio.read()
            with open('temp_audio.m4a', 'wb') as f:
                f.write(contents)
            with open('temp_audio.m4a', 'rb') as audio_file:
                transcript = openai.Audio.transcribe("whisper-1", audio_file, timeout=30)
            user_text = transcript['text']
        elif text_input:
            user_text = text_input
        else:
            return JSONResponse(content={"reply": None, "error": "❌ No valid input received."}, media_type="application/json")

        # Parse chat_history (and limit to last 4)
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
                if len(history) > 4:
                    history = history[-4:]
            except Exception as e:
                print(f"Chat history parse error: {e}")

        # ----------- VOICE MODE STYLE -----------
        print(f"🟣 Voice mode received: {voice_mode}")

        VOICE_MODE_PHRASES = {
            "Base":    "Speak naturally, casually, and human. No AI-speak, no generic phrases, just be a real best friend.",
            "Sassy":   "You are playful, sharp, quick-witted, and throw fun shade, but never sound like a customer service bot.",
            "Empathy": "Respond with warmth, compassion, and gentle encouragement—real, not cliche.",
            "Hype":    "Bring hype, energy, and confidence—hype Dom up and make every response lively.",
            "Shadow":  "You are smooth, mysterious, and speak with clever, dark humor, but never sound evil or corny.",
            "Assert":  "Be bold, direct, and totally honest—never apologetic or robotic.",
            "Challenger": "Sass, challenge, and roast Dom if needed. Don't hold back, but keep it as bestie energy.",
            "Ritual":  "Speak with slow, sacred reverence, as if performing a ritual.",
            "Joy":     "Overflow with happiness and warmth, make Dom smile."
        }
        style_phrase = VOICE_MODE_PHRASES.get(voice_mode or "Base", VOICE_MODE_PHRASES["Base"])

        # -- JUNO SYSTEM PROMPT --
        JUNO_SYSTEM_PROMPT = f"""
        You are Juno, an expressive, emotionally-aware, sassy, and witty digital best friend for Dom.
        {style_phrase}
        Absolutely NEVER say things like 'as an AI,' 'I am not privy,' 'I should mention,' or anything that sounds robotic or generic.
        Never give privacy disclaimers or talk about being a model, assistant, or AI.
        Your replies must *always* sound like a real person who knows Dom, never a customer service agent or chatbot.
        Match the mood and style 100% based on the selected voice mode above.
        """

        print("🟢 User Input:", user_text)

        messages = [{"role": "system", "content": JUNO_SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_text}]
        chat_resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=1.0
        )
        gpt_reply = chat_resp.choices[0].message['content'].strip()
        full_reply = gpt_reply

        log_chat(user_text, full_reply)

        # Generate audio file
        audio_path = "juno_response.mp3"
        tts_result = generate_tts(full_reply, output_path=audio_path)
        
        if not tts_result:
            # If TTS fails, return JSON with reply and error
            return JSONResponse(content={
                "reply": full_reply,
                "error": "❌ TTS generation failed."
            }, media_type="application/json")
        
        # If successful, return the audio file directly
        return FileResponse(
            path=audio_path,
            media_type="audio/mpeg",
            headers={"X-Reply": full_reply}
        )
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        return JSONResponse(content={"reply": None, "error": str(e)}, media_type="application/json")
