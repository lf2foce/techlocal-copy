import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Set per-user in future

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_telegram_message(text: str, chat_id: str = CHAT_ID):
    if not TELEGRAM_TOKEN or not chat_id:
        print("[WARN] Telegram token or chat_id not set")
        return

    try:
        response = httpx.post(
            f"{BASE_URL}/sendMessage",
            data={"chat_id": chat_id, "text": text}
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        print(f"[ERROR] Telegram message failed: {e}")
