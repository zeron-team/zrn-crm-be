"""
Security module — Rust-powered crypto for ZeRoN 360°
Uses rust_core (compiled via maturin/PyO3) for:
  - Argon2id password hashing (replaces bcrypt for new passwords)
  - bcrypt verification (backward compat for existing passwords)
  - JWT create/decode (native Rust, replaces python-jose)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.redis_cache import blacklist_token, is_token_blacklisted, store_token

logger = logging.getLogger(__name__)

# Try to import Rust module; fall back to Python if not available
try:
    import rust_core as _rc
    RUST_AVAILABLE = True
    logger.info("🦀 rust_core loaded — using Rust crypto (Argon2id + native JWT)")
except ImportError:
    RUST_AVAILABLE = False
    logger.warning("⚠️ rust_core not available — falling back to Python crypto")
    from passlib.context import CryptContext
    from jose import JWTError, jwt
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password. Supports Argon2id (new) and bcrypt (legacy)."""
    if RUST_AVAILABLE:
        return _rc.verify_password(plain_password, hashed_password)
    return _pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password with Argon2id (Rust) or bcrypt (fallback)."""
    if RUST_AVAILABLE:
        return _rc.hash_password(password)
    return _pwd_context.hash(password)


def is_legacy_hash(hashed_password: str) -> bool:
    """Check if password is using legacy bcrypt (needs re-hash on login)."""
    if RUST_AVAILABLE:
        return _rc.is_legacy_hash(hashed_password)
    return False  # If using Python, everything is bcrypt


def maybe_upgrade_hash(plain_password: str, current_hash: str, update_callback=None) -> None:
    """
    If the hash is legacy bcrypt, re-hash with Argon2id.
    Call this on successful login for gradual migration.
    update_callback(new_hash) should persist the new hash.
    """
    if RUST_AVAILABLE and is_legacy_hash(current_hash):
        new_hash = get_password_hash(plain_password)
        if update_callback:
            update_callback(new_hash)
            logger.info("🔐 Password upgraded from bcrypt to Argon2id")


def create_access_token(data: dict, secret_key: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token (Rust-native or python-jose fallback)."""
    ttl_minutes = int((expires_delta or timedelta(minutes=480)).total_seconds() // 60)

    if RUST_AVAILABLE:
        payload = {k: str(v) for k, v in data.items()}
        token = _rc.create_jwt(payload, secret_key, ttl_minutes)
    else:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=480))
        to_encode.update({"exp": expire})
        token = jwt.encode(to_encode, secret_key, algorithm="HS256")

    # Store in Redis
    user_id = data.get("sub", 0)
    store_token(user_id, token, ttl_minutes)
    return token


def decode_token(token: str, secret_key: str) -> dict | None:
    """Decode JWT token. Checks Redis blacklist first."""
    if is_token_blacklisted(token):
        return None

    if RUST_AVAILABLE:
        return _rc.decode_jwt(token, secret_key)
    else:
        try:
            return jwt.decode(token, secret_key, algorithms=["HS256"])
        except JWTError:
            return None


def invalidate_token(token: str) -> bool:
    """Invalidate a token (logout). Blacklists in Redis."""
    return blacklist_token(token, ttl_minutes=480)
