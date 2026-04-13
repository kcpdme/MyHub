"""Outbound webhook dispatcher.

Fires HTTP POST requests to all active WebhookSubscription records that
match a given event type.  Each delivery is logged to WebhookDeliveryLog.

Delivery runs in a background daemon thread so it never blocks the request.

Supported event types
---------------------
task.created        task.updated        task.done
capture.created     capture.deleted
note.created        note.updated        note.deleted
reminder.sent       reminder.created
inbox.saved         inbox.archived
"""
from __future__ import annotations

import hmac
import hashlib
import json
import threading
from datetime import datetime
from typing import Any

import httpx

from app.database import SessionLocal
from app import models


# Timeout for each outbound HTTP request.
_DELIVERY_TIMEOUT_SECONDS = 10


def _sign_payload(secret: str, payload_bytes: bytes) -> str:
    """Return HMAC-SHA256 hex digest of the payload, prefixed with 'sha256='."""
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def _deliver_to_subscription(
    subscription_id: int,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Fire the webhook and log the result.  Runs in a background thread."""
    db = SessionLocal()
    try:
        sub = db.query(models.WebhookSubscription).filter(
            models.WebhookSubscription.id == subscription_id,
            models.WebhookSubscription.is_active.is_(True),
        ).first()
        if not sub:
            return

        payload_bytes = json.dumps(payload, default=str).encode()
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Event": event_type,
            "User-Agent": "AutomationHub/2.0",
        }
        if sub.secret:
            headers["X-Hub-Signature-256"] = _sign_payload(sub.secret, payload_bytes)

        response_status: int | None = None
        success = False
        error_message = ""

        try:
            resp = httpx.post(
                sub.url,
                content=payload_bytes,
                headers=headers,
                timeout=_DELIVERY_TIMEOUT_SECONDS,
                follow_redirects=True,
            )
            response_status = resp.status_code
            success = resp.is_success
            if not success:
                error_message = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            error_message = str(exc)[:500]

        # Log the delivery attempt.
        db.add(models.WebhookDeliveryLog(
            subscription_id=subscription_id,
            event_type=event_type,
            payload_json=json.dumps(payload, default=str),
            response_status=response_status,
            success=success,
            error_message=error_message,
        ))
        sub.last_fired_at = datetime.utcnow()
        db.add(sub)
        db.commit()
    finally:
        db.close()


def fire_event(event_type: str, payload: dict[str, Any]) -> None:
    """Enqueue webhook deliveries for all active subscriptions matching event_type.

    Each delivery is dispatched in a separate daemon thread so active request
    processing is never blocked.
    """
    db = SessionLocal()
    try:
        subs = (
            db.query(models.WebhookSubscription)
            .filter(models.WebhookSubscription.is_active.is_(True))
            .all()
        )
        matching_ids = []
        for sub in subs:
            registered = [e.strip() for e in sub.event_types.split(",")]
            if "*" in registered or event_type in registered:
                matching_ids.append(sub.id)
    finally:
        db.close()

    full_payload = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": payload,
    }
    for sub_id in matching_ids:
        t = threading.Thread(
            target=_deliver_to_subscription,
            args=(sub_id, event_type, full_payload),
            daemon=True,
        )
        t.start()
