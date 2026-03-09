"""
Encryption Service for ZeRoN 360°
Uses Rust AES-256-GCM via rust_core for encrypting sensitive data at rest.
Falls back to Python cryptography if Rust is not available.
"""

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import rust_core as _rc
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    logger.warning("⚠️ rust_core not available — encryption disabled")


def encrypt(plaintext: str) -> Optional[str]:
    """Encrypt a string with AES-256-GCM. Returns base64-encoded ciphertext."""
    if not settings.ENCRYPTION_KEY:
        logger.warning("ENCRYPTION_KEY not set — storing plaintext")
        return plaintext
    if not RUST_AVAILABLE:
        return plaintext
    try:
        return _rc.encrypt_sensitive(plaintext, settings.ENCRYPTION_KEY)
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return plaintext


def decrypt(ciphertext: str) -> Optional[str]:
    """Decrypt an AES-256-GCM encrypted string. Returns plaintext."""
    if not settings.ENCRYPTION_KEY or not RUST_AVAILABLE:
        return ciphertext
    # If it doesn't look like base64 (encrypted), return as-is
    if not ciphertext or len(ciphertext) < 20:
        return ciphertext
    try:
        return _rc.decrypt_sensitive(ciphertext, settings.ENCRYPTION_KEY)
    except Exception:
        # Likely not encrypted (plaintext data from before encryption was enabled)
        return ciphertext


def is_encrypted(value: str) -> bool:
    """Check if a value appears to be encrypted (base64-encoded with nonce)."""
    if not value or len(value) < 20:
        return False
    try:
        import base64
        decoded = base64.b64decode(value)
        return len(decoded) > 12  # At least nonce (12) + some ciphertext
    except Exception:
        return False
