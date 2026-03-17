"""WhatsApp Notification Sender — uses the existing WhatsApp bridge service."""
import logging
import httpx
import os

logger = logging.getLogger(__name__)

# The WhatsApp bridge runs as a separate service
WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://127.0.0.1:3001")


def send_whatsapp_notification(
    phone_number: str,
    title: str,
    body: str,
) -> dict:
    """
    Send a notification via the existing WhatsApp bridge.
    Requires the user's mobile number and a running whatsapp-service.
    Returns {"success": True/False, "error": "..."}.
    """
    if not phone_number:
        return {"success": False, "error": "No tenés un número de celular configurado en tu perfil"}

    try:
        # Normalize phone number: remove spaces, dashes, etc.
        clean_number = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not clean_number.startswith("+"):
            clean_number = f"+{clean_number}"

        text = f"🔔 *{title}*\n\n{body}\n\n_Zeron CRM 360°_"

        payload = {
            "phone": clean_number,
            "message": text,
        }

        with httpx.Client(timeout=15) as client:
            response = client.post(
                f"{WHATSAPP_SERVICE_URL}/send-new",
                json=payload,
            )

        if response.status_code == 200:
            logger.info(f"✅ WhatsApp notification sent to {clean_number}")
            return {"success": True, "error": None}
        else:
            error = response.text
            logger.error(f"❌ WhatsApp bridge error: {error}")
            return {"success": False, "error": error}

    except httpx.ConnectError:
        msg = "El servicio de WhatsApp no está activo. Inicialo con: cd whatsapp-service && node server.js"
        logger.error(f"❌ WhatsApp: {msg}")
        return {"success": False, "error": msg}
    except Exception as e:
        logger.error(f"❌ WhatsApp notification failed: {e}")
        return {"success": False, "error": str(e)}
