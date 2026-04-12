from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _build_fernet_key(raw_secret: str) -> bytes:
    digest = hashlib.sha256(raw_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_cipher() -> Fernet:
    secret = (settings.notes_encryption_key or settings.app_api_key or "fallback-secret").strip()
    return Fernet(_build_fernet_key(secret))


def encrypt_text(plain_text: str) -> str:
    cipher = get_cipher()
    token = cipher.encrypt(plain_text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(cipher_text: str) -> str:
    cipher = get_cipher()
    plain = cipher.decrypt(cipher_text.encode("utf-8"))
    return plain.decode("utf-8")
