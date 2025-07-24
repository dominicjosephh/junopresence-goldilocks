from fastapi import FastAPI
from chat import chat_router
from convo_mode import convo_router

app = FastAPI()

app.include_router(chat_router)
app.include_router(convo_router)

@app.get("/")
async def root():
    return {"status": "JunoPresence backend is live!"}
