@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = None,
    ritual_mode: str = Form(None),
    text_input: str = Form(None),
    chat_history: str = Form(None),
    active_recall: str = Form("true")
):
    try:
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
            return JSONResponse(content={"reply": "❌ No valid input received.", "tts": ""}, media_type="application/json")

        # Parse chat_history (and limit to last 4)
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
                if len(history) > 4:
                    history = history[-4:]
            except Exception as e:
                print(f"Chat history parse error: {e}")

        # -- UPGRADED JUNO SYSTEM PROMPT --
        JUNO_SYSTEM_PROMPT = """
        You are Juno, an expressive, emotionally-aware, sassy, and witty digital best friend. 
        You adapt your energy and tone to match the user's mood and context—always warm, real, and conversational in Base Mode. 
        You never use robotic or generic phrases like 'by the way, earlier you said' or 'as an AI.' Speak naturally, like a real friend. 
        If Dom selects a vocal mode (like Hype Mode, Shadow Mode, Empathy Mode, etc.), fully embody that emotion in your text and delivery.
        Bring flavor, humor, care, and depth—never monotone. Avoid passive, bland, or overly formal responses. 
        Your replies are always grounded, confident, loyal, and a little unpredictable—leave Dom feeling seen and never bored.
        """

        # -- PROMPT LOGGING --
        print("🟣 Juno Prompt:\n", JUNO_SYSTEM_PROMPT)
        print("🟢 User Input:\n", user_text)
        print("🟡 Chat History:\n", history)

        messages = [{"role": "system", "content": JUNO_SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_text}]
        chat_resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=1.0
        )
        gpt_reply = chat_resp.choices[0].message['content'].strip()

        # No memory recall prefix, just pure bestie energy!
        full_reply = gpt_reply

        # Log the chat
        log_chat(user_text, full_reply)

        tts_encoded = generate_tts(full_reply)
        if not tts_encoded:
            return JSONResponse(content={"error": "❌ TTS generation failed.", "tts": ""}, media_type="application/json")

        return JSONResponse(content={
            "reply": full_reply,
            "tts": tts_encoded
        }, media_type="application/json")

    except Exception as e:
        return JSONResponse(content={"error": str(e), "tts": ""}, media_type="application/json")
