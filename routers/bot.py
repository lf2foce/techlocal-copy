import os
import httpx
from fastapi import APIRouter, Request
from contextlib import asynccontextmanager
from services.telegram_handler import send_telegram_message
from services.logger import logger
from services.telegram_handler import (
    start, list_campaigns, create_campaign,
    generate_themes, list_themes, select_theme,
    list_posts, view_post, redo_post
)

telegram_router = APIRouter(tags=["Telegram"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")

@asynccontextmanager
async def telegram_lifespan(app):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_URL:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
                    params={"url": TELEGRAM_WEBHOOK_URL},
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"Telegram webhook set at {TELEGRAM_WEBHOOK_URL}")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}")
    yield

@telegram_router.get("/ping")
def ping():
    return {"message": "pong"}

@telegram_router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        message = data.get("message")
        if not message:
            return {"ok": True}

        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        parts = text.strip().split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd == "/start":
                reply = start()
            elif cmd == "/campaigns":
                reply = await list_campaigns()
            elif cmd == "/create_campaign":
                if len(args) < 5:
                    reply = "Usage: /create_campaign <title> <days> <target_customer> <insight> <desc>"
                else:
                    title = args[0]
                    days = int(args[1])
                    target = args[2]
                    insight = args[3]
                    desc = " ".join(args[4:])
                    reply = await create_campaign(title, days, target, insight, desc)
            elif cmd == "/generate_themes":
                if not args:
                    reply = "Usage: /generate_themes <campaign_id> - Generate 5 unique themes for your campaign"
                else:
                    reply = await generate_themes(args[0])
            elif cmd == "/themes":
                if not args:
                    reply = "Usage: /themes <campaign_id> - View all themes for your campaign"
                else:
                    reply = await list_themes(args[0])
            elif cmd == "/select_theme":
                if not args:
                    reply = "Usage: /select_theme <theme_id> - Choose a theme and start generating posts"
                else:
                    reply = await select_theme(args[0])
            elif cmd == "/posts":
                if not args:
                    reply = "Usage: /posts <campaign_id> - View all posts in your campaign"
                else:
                    reply = await list_posts(args[0])
            elif cmd == "/view_post":
                if not args:
                    reply = "Usage: /view_post <post_id> - See the full content of a specific post"
                else:
                    reply = await view_post(int(args[0]))
            elif cmd == "/redo_post":
                if not args:
                    reply = "Usage: /redo_post <post_id> - Not happy with a post? Regenerate it!"
                else:
                    reply = await redo_post(args[0])
            else:
                reply = "Unknown command. Try /start"

            await send_telegram_message(reply, chat_id)

        except Exception as e:
            await send_telegram_message(f"⚠️ Error: {str(e)}", chat_id)

        return {"ok": True}

    except Exception as e:
        return {"ok": False, "error": str(e)}
