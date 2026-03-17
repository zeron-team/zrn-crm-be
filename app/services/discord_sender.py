"""Discord Notification Sender — uses Discord Webhook URLs."""
import logging
import httpx

logger = logging.getLogger(__name__)


def send_discord_notification(
    webhook_url: str,
    title: str,
    body: str,
) -> dict:
    """
    Send a notification via Discord Webhook.
    Uses rich embed format for a professional look.
    Returns {"success": True/False, "error": "..."}.
    """
    if not webhook_url:
        return {"success": False, "error": "No tenés una URL de Webhook de Discord configurada en tu perfil"}

    try:
        payload = {
            "username": "Zeron CRM 360°",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
            "embeds": [
                {
                    "title": f"🔔 {title}",
                    "description": body,
                    "color": 0x6366F1,  # Indigo color matching CRM branding
                    "footer": {
                        "text": "Zeron CRM 360°"
                    },
                }
            ],
        }

        with httpx.Client(timeout=10) as client:
            response = client.post(webhook_url, json=payload)

        # Discord returns 204 No Content on success
        if response.status_code in (200, 204):
            logger.info("✅ Discord notification sent")
            return {"success": True, "error": None}
        else:
            error = response.text
            logger.error(f"❌ Discord Webhook error: {error}")
            return {"success": False, "error": error}

    except Exception as e:
        logger.error(f"❌ Discord notification failed: {e}")
        return {"success": False, "error": str(e)}
