from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import convo_mode  # Import the convo_mode router module

app = FastAPI()

# Enable CORS (allow all origins for simplicity; adjust as needed for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the conversation mode routes under the "/api" prefix
app.include_router(convo_mode.router, prefix="/api")

# (Optional) A simple health check endpoint
@app.get("/")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # Run the app with Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
