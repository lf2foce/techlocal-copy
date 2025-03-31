from fastapi import FastAPI
import requests

from routers.campaigns import router as campaigns_router
from routers.themes import router as themes_router
from routers.scheduler import router as scheduler_router
from routers.content import router as content_router

from database.models import Base  # This imports all your models
from database.db import engine, SessionLocal, get_db

from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your-telegram-bot-token")
# TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your-telegram-chat-id")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Create database tables
#     Base.metadata.create_all(bind=engine)
    
#     # Set Telegram webhook at startup
#     try:
#         res = requests.get(
#             f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
#             params={"url": TELEGRAM_WEBHOOK_URL}
#         )
#         print("Webhook set response:", res.json())
#     except Exception as e:
#         print("Failed to set webhook:", e)
    
#     yield  # Run the app

app = FastAPI(title="Content Generation API") #, lifespan=lifespan

# Register routers
app.include_router(campaigns_router)
app.include_router(themes_router)
app.include_router(scheduler_router)
app.include_router(content_router)
@app.get("/")
def read_root():
    return {"message": "Campaign system running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)