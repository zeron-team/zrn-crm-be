"""Email Notification Sender — uses user's default SMTP account."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def send_email_notification(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_ssl: bool,
    from_addr: str,
    to_addr: str,
    subject: str,
    body: str,
) -> dict:
    """
    Send a notification email using the user's SMTP configuration.
    Returns {"success": True/False, "error": "..."}.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg["Subject"] = subject

        # HTML body with Zeron CRM branding
        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 20px 24px; border-radius: 12px 12px 0 0;">
                <h2 style="color: white; margin: 0; font-size: 18px;">🔔 {subject}</h2>
            </div>
            <div style="background: #ffffff; padding: 24px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 12px 12px;">
                <p style="color: #374151; line-height: 1.6; margin: 0;">{body}</p>
                <hr style="border: none; border-top: 1px solid #f3f4f6; margin: 16px 0;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">Enviado desde Zeron CRM 360°</p>
            </div>
        </div>
        """
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        if smtp_ssl and smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            if smtp_ssl:
                server.starttls()

        server.login(smtp_user, smtp_password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
        server.quit()

        logger.info(f"✅ Email notification sent to {to_addr}")
        return {"success": True, "error": None}

    except Exception as e:
        logger.error(f"❌ Email notification failed: {e}")
        return {"success": False, "error": str(e)}
