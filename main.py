from fastapi import FastAPI, Request
import requests

from routers.campaigns import router as campaigns_router
from routers.themes import router as themes_router
from routers.scheduler import router as scheduler_router
from routers.content import router as content_router
from routers.bot import telegram_router , telegram_lifespan

from services.init_gemini import init_vertexai
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

load_dotenv()

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your-telegram-chat-id")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Vertex AI before starting the app
    init_vertexai()
    async with telegram_lifespan(app):
        yield

app = FastAPI(lifespan=lifespan)
# Remove init_vertexai() from here since it's now in lifespan

# Register routers
app.include_router(campaigns_router)
app.include_router(themes_router)
app.include_router(scheduler_router)
app.include_router(content_router)
app.include_router(telegram_router)
@app.get("/")
def read_root():
    return {"message": "Campaign system running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)