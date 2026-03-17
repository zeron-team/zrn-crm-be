"""Telegram Notification Sender — uses Telegram Bot API."""
import logging
import httpx
import os

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_BASE = "https://api.telegram.org"


def send_telegram_notification(
    chat_id: str,
    title: str,
    body: str,
) -> dict:
    """
    Send a notification via Telegram Bot API.
    Requires TELEGRAM_BOT_TOKEN env var and user's chat_id.
    Returns {"success": True/False, "error": "..."}.
    """
    if not TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN no está configurado en el servidor"}

    if not chat_id:
        return {"success": False, "error": "No tenés un Chat ID de Telegram configurado en tu perfil"}

    try:
        text = f"🔔 *{_escape_md(title)}*\n\n{_escape_md(body)}\n\n_{_escape_md('Zeron CRM 360°')}_"

        url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
        }

        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=payload)

        if response.status_code == 200:
            logger.info(f"✅ Telegram notification sent to chat_id {chat_id}")
            return {"success": True, "error": None}
        else:
            error = response.text
            logger.error(f"❌ Telegram API error: {error}")
            return {"success": False, "error": error}

    except Exception as e:
        logger.error(f"❌ Telegram notification failed: {e}")
        return {"success": False, "error": str(e)}


def _escape_md(text: str) -> str:
    """Escape special characters for MarkdownV2."""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    escaped = ""
    for char in text:
        if char in special_chars:
            escaped += f"\\{char}"
        else:
            escaped += char
    return escaped
