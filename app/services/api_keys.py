from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app import models


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def ensure_bootstrap_api_key(db: Session, plain_key: str) -> None:
    key = plain_key.strip()
    if not key:
        return

    key_hash = hash_api_key(key)
    existing = db.query(models.ApiKey).filter(models.ApiKey.key_hash == key_hash).first()
    if existing:
        return

    db.add(
        models.ApiKey(
            name="bootstrap-env",
            key_hash=key_hash,
            is_active=True,
        )
    )
    db.commit()


def validate_api_key(db: Session, plain_key: str) -> bool:
    key = plain_key.strip()
    if not key:
        return False

    key_hash = hash_api_key(key)
    record = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.key_hash == key_hash)
        .filter(models.ApiKey.is_active.is_(True))
        .first()
    )
    if not record:
        return False

    record.last_used_at = datetime.utcnow()
    db.add(record)
    db.commit()
    return True
