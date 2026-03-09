"""
ZeRoN 360° — Module Licensing System
======================================
Offline-capable license validation using HMAC-SHA256 signatures.

License format: base64({json_payload}.{hmac_signature})

Payload: {
    "module": "crm",
    "company_cuit": "30-71657610-9",
    "max_users": 10,
    "expires_at": "2027-01-01",
    "plan": "professional"
}
"""

import json
import hmac
import hashlib
import base64
import logging
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

LICENSE_SECRET = getattr(settings, "LICENSE_SECRET", "zeron-360-default-dev-key")


@dataclass
class LicenseInfo:
    module: str
    company_cuit: str
    max_users: int
    expires_at: Optional[datetime]
    plan: str  # "trial", "starter", "professional", "enterprise"
    valid: bool
    message: str


def generate_license(
    module: str,
    company_cuit: str,
    max_users: int = 0,
    expires_at: str = "2027-12-31",
    plan: str = "professional",
) -> str:
    """Generate a signed license key for a module."""
    payload = {
        "module": module,
        "company_cuit": company_cuit,
        "max_users": max_users,
        "expires_at": expires_at,
        "plan": plan,
        "issued_at": datetime.utcnow().isoformat(),
    }
    payload_json = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        LICENSE_SECRET.encode(),
        payload_json.encode(),
        hashlib.sha256,
    ).hexdigest()

    token = base64.urlsafe_b64encode(
        f"{payload_json}|{signature}".encode()
    ).decode()

    return token


def validate_license(license_key: str) -> LicenseInfo:
    """Validate a license key and return its info."""
    try:
        decoded = base64.urlsafe_b64decode(license_key.encode()).decode()
        parts = decoded.rsplit("|", 1)
        if len(parts) != 2:
            return LicenseInfo("", "", 0, None, "invalid", False, "Formato de licencia inválido")

        payload_json, signature = parts

        # Verify HMAC signature
        expected_sig = hmac.new(
            LICENSE_SECRET.encode(),
            payload_json.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return LicenseInfo("", "", 0, None, "invalid", False, "Firma de licencia inválida")

        payload = json.loads(payload_json)

        # Check expiration
        expires_at = None
        if payload.get("expires_at"):
            expires_at = datetime.fromisoformat(payload["expires_at"])
            if expires_at < datetime.utcnow():
                return LicenseInfo(
                    module=payload.get("module", ""),
                    company_cuit=payload.get("company_cuit", ""),
                    max_users=payload.get("max_users", 0),
                    expires_at=expires_at,
                    plan=payload.get("plan", "expired"),
                    valid=False,
                    message=f"Licencia expirada el {expires_at.strftime('%d/%m/%Y')}",
                )

        return LicenseInfo(
            module=payload.get("module", ""),
            company_cuit=payload.get("company_cuit", ""),
            max_users=payload.get("max_users", 0),
            expires_at=expires_at,
            plan=payload.get("plan", "trial"),
            valid=True,
            message="Licencia válida",
        )

    except Exception as e:
        logger.error(f"License validation error: {e}")
        return LicenseInfo("", "", 0, None, "error", False, f"Error: {str(e)}")
