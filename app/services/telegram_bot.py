"""Telegram bot worker.

Operating modes
---------------
Webhook mode (preferred for multi-server):
    Set TELEGRAM_WEBHOOK_URL to your public HTTPS endpoint.
    The bot registers the webhook with Telegram on startup and skips polling.
    Incoming updates are received at POST /telegram/webhook.

Long-polling mode (default, single-server):
    TELEGRAM_WEBHOOK_URL is empty.
    A background thread calls getUpdates in a loop.

In both modes message handling is done by _handle_message().
"""
from __future__ import annotations

import threading
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import SessionLocal
from app.services.crypto_service import decrypt_text, encrypt_text
from app.services.media_storage import is_r2_enabled, media_object_key, put_media_to_r2
from app.services.summary_service import get_today_summary


# ─── Webhook registration ─────────────────────────────────────────────────────

def register_webhook() -> None:
    """Tell Telegram to push updates to TELEGRAM_WEBHOOK_URL."""
    if not settings.telegram_bot_token or not settings.telegram_webhook_url:
        return

    base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
    payload: dict = {"url": settings.telegram_webhook_url}
    if settings.telegram_webhook_secret:
        payload["secret_token"] = settings.telegram_webhook_secret

    try:
        resp = httpx.post(f"{base}/setWebhook", json=payload, timeout=15)
        if resp.is_success and resp.json().get("ok"):
            print(f"[telegram] Webhook registered: {settings.telegram_webhook_url}")
        else:
            print(f"[telegram] Webhook registration failed: {resp.text}")
    except Exception as exc:
        print(f"[telegram] Webhook registration error: {exc}")


def delete_webhook() -> None:
    """Remove a previously registered webhook (called on shutdown)."""
    if not settings.telegram_bot_token:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/deleteWebhook",
            timeout=10,
        )
    except Exception:
        pass


# ─── Message handler (shared by polling and webhook modes) ────────────────────

def handle_telegram_update(update: dict) -> None:
    """Process a single Telegram update dict."""
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = str(chat.get("id", "")).strip()
    telegram_user_id = str(from_user.get("id", "")).strip()

    if chat_id and telegram_user_id:
        base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        with httpx.Client(timeout=15) as client:
            _handle_message(client, base_url, chat_id, telegram_user_id, text, message)


# ─── Long-polling worker ──────────────────────────────────────────────────────

class TelegramBotWorker:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset = 0

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        if not settings.telegram_bot_token:
            return
        if settings.telegram_webhook_url:
            # Webhook mode — no polling thread needed.
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="telegram-bot-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

        with httpx.Client(timeout=max(settings.telegram_bot_poll_timeout_seconds + 5, 10)) as client:
            if settings.telegram_poll_drop_pending_on_start:
                try:
                    # Drop stale queued updates from before restart/deploy.
                    flush_resp = client.get(
                        f"{base_url}/getUpdates",
                        params={"timeout": 0, "offset": -1, "limit": 1},
                    )
                    flush_resp.raise_for_status()
                    flush_data = flush_resp.json()
                    if flush_data.get("ok"):
                        latest = flush_data.get("result") or []
                        if latest:
                            update_id = int(latest[-1].get("update_id", 0) or 0)
                            if update_id:
                                self._offset = update_id + 1
                        print("[telegram] Drained pending updates on startup.")
                except Exception as exc:
                    print(f"[telegram] Pending update drain skipped: {exc}")

            while not self._stop_event.is_set():
                try:
                    params: dict = {
                        "timeout": max(settings.telegram_bot_poll_timeout_seconds, 5),
                        "allowed_updates": '["message","web_app_data"]',
                    }
                    if self._offset:
                        params["offset"] = self._offset

                    response = client.get(f"{base_url}/getUpdates", params=params)
                    response.raise_for_status()
                    data = response.json()
                    if not data.get("ok"):
                        time.sleep(1)
                        continue

                    for update in data.get("result", []):
                        update_id = int(update.get("update_id", 0))
                        if update_id:
                            self._offset = update_id + 1

                        message = update.get("message") or {}
                        text = (message.get("text") or "").strip()
                        chat = message.get("chat") or {}
                        from_user = message.get("from") or {}
                        chat_id = str(chat.get("id", "")).strip()
                        telegram_user_id = str(from_user.get("id", "")).strip()

                        if chat_id and telegram_user_id:
                            _handle_message(client, base_url, chat_id, telegram_user_id, text, message)
                except Exception:
                    time.sleep(2)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _send_text(client: httpx.Client, base_url: str, chat_id: str, text: str) -> None:
    try:
        client.post(f"{base_url}/sendMessage", json={"chat_id": chat_id, "text": text})
    except Exception:
        pass


def _send_menu(client: httpx.Client, base_url: str, chat_id: str, text: str = "Choose an action:") -> None:
    """Send a reply keyboard menu AND an inline 'Open Dashboard' web_app button."""
    miniapp_url = settings.miniapp_url or ""

    # Inline keyboard with Mini App button (shown above text input).
    inline_markup = None
    if miniapp_url:
        inline_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "🚀 Open Dashboard",
                        "web_app": {"url": miniapp_url},
                    }
                ]
            ]
        }

    # Reply keyboard for quick command shortcuts.
    reply_keyboard = {
        "keyboard": [
            [{"text": "/summary"}, {"text": "/task list"}],
            [{"text": "/note list"}, {"text": "/inbox list"}],
            [{"text": "/reminder list"}],
            [{"text": "/help"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }
    try:
        # First send the inline keyboard with the Mini App button.
        if inline_markup:
            client.post(
                f"{base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "reply_markup": inline_markup,
                    "parse_mode": "HTML",
                },
            )
        else:
            client.post(
                f"{base_url}/sendMessage",
                json={"chat_id": chat_id, "text": text, "reply_markup": reply_keyboard},
            )
    except Exception:
        pass


def _is_allowed_user(db: Session, telegram_user_id: str) -> bool:
    return (
        db.query(models.AllowedTelegramUser)
        .filter(models.AllowedTelegramUser.telegram_user_id == telegram_user_id)
        .filter(models.AllowedTelegramUser.is_active.is_(True))
        .first()
        is not None
    )


def _extract_inbox_item(message: dict) -> tuple[str, str, str, str, str]:
    text = (message.get("text") or "").strip()
    caption = (message.get("caption") or "").strip()

    if text:
        return "text", text, "", "", str(message.get("media_group_id", "") or "")

    photo = message.get("photo") or []
    if photo:
        best = photo[-1]
        content = caption or "[photo]"
        return (
            "photo", content,
            str(best.get("file_id", "") or ""),
            str(best.get("file_unique_id", "") or ""),
            str(message.get("media_group_id", "") or ""),
        )

    for media_type in ["document", "video", "audio", "voice", "animation", "sticker"]:
        media_obj = message.get(media_type)
        if media_obj:
            if media_type == "document":
                filename = str(media_obj.get("file_name", "") or "").strip()
                content = caption or (f"[document] {filename}".strip() if filename else "[document]")
            else:
                content = caption or f"[{media_type}]"
            return (
                media_type, content,
                str(media_obj.get("file_id", "") or ""),
                str(media_obj.get("file_unique_id", "") or ""),
                str(message.get("media_group_id", "") or ""),
            )

    if message.get("location"):
        location = message.get("location") or {}
        content = f"[location] {location.get('latitude')}, {location.get('longitude')}"
        return "location", content, "", "", ""

    return "unknown", "[unsupported message type]", "", "", ""


def _store_inbox_item(db: Session, telegram_user_id: str, chat_id: str, message: dict) -> models.TelegramInboxItem:
    item_type, content, file_id, file_unique_id, media_group_id = _extract_inbox_item(message)
    item = models.TelegramInboxItem(
        source="telegram",
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        message_id=int(message.get("message_id", 0) or 0),
        item_type=item_type,
        text=content,
        file_id=file_id,
        file_unique_id=file_unique_id,
        media_group_id=media_group_id,
        raw_json=json.dumps(message, ensure_ascii=True),
        is_archived=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _handle_message(
    client: httpx.Client,
    base_url: str,
    chat_id: str,
    telegram_user_id: str,
    text: str,
    message: dict,
) -> None:
    db: Session = SessionLocal()
    try:
        if text and text.startswith("/"):
            print(f"[telegram] cmd user={telegram_user_id} chat={chat_id} text={text[:80]}")

        # ── Strip @botname from commands ──
        if text.startswith("/"):
            first_space = text.find(" ")
            if first_space != -1:
                cmd = text[:first_space]
                args = text[first_space:]
            else:
                cmd = text
                args = ""

            if "@" in cmd:
                cmd = cmd.split("@")[0]
                text = cmd + args

        lowered = text.lower()

        # ── Public commands (no allowlist required) ──
        if lowered in {"/id", "/whoami"}:
            _send_text(client, base_url, chat_id, f"telegram_user_id: {telegram_user_id}")
            return

        if lowered in {"/start", "/help", "/menu"}:
            miniapp_url = settings.miniapp_url or ""
            miniapp_hint = f"\n\n🚀 <b>Tap the button above to open the full dashboard</b> inside Telegram." if miniapp_url else ""
            _send_menu(
                client, base_url, chat_id,
                "<b>AutoHub Commands</b>\n"
                "/id\n/menu\n/summary\n"
                "/note add &lt;content&gt;\n/note list\n/note read &lt;id&gt;\n"
                "/task add &lt;title&gt;\n/task done &lt;id or partial title&gt;\n/task list\n"
                "/capture &lt;text&gt;\n/inbox list\n"
                "/reminder list\n/remind &lt;minutes&gt; &lt;message&gt;"
                + miniapp_hint,
            )
            return

        # ── Allowlist check ──
        if not _is_allowed_user(db, telegram_user_id):
            _send_text(
                client, base_url, chat_id,
                f"Access denied. Ask admin to allow telegram_user_id: {telegram_user_id}",
            )
            return

        # ── Shorthand command aliases ──
        # Map single-word commands to their multi-word equivalents so users
        # can type /notes instead of /note list, etc.
        _ALIASES = {
            "/notes": "/note list",
            "/tasks": "/task list",
            "/reminders": "/reminder list",
            "/captures": "/capture list",
            "/inbox": "/inbox list",
        }
        if lowered.strip() in _ALIASES:
            lowered = _ALIASES[lowered.strip()]
            text = lowered  # rewrite for downstream handlers

        # ── /note read <id> or bare #<id> ──
        note_id = None
        if lowered.startswith("/note read "):
            candidate = text[11:].strip().lstrip("#")
            if candidate.isdigit():
                note_id = int(candidate)
        elif text.strip().startswith("#"):
            candidate = text.strip()[1:]
            if candidate.isdigit():
                note_id = int(candidate)

        if note_id is not None:
            note = db.query(models.EncryptedNote).filter(models.EncryptedNote.id == note_id).first()
            if not note:
                _send_text(client, base_url, chat_id, f"Note not found: #{note_id}")
                return
            try:
                content = decrypt_text(note.cipher_text)
            except Exception:
                content = "<decrypt-error>"

            title = note.title.strip()
            if title:
                _send_text(client, base_url, chat_id, f"Note #{note.id} - {title}\n\n{content}")
            else:
                _send_text(client, base_url, chat_id, f"Note #{note.id}\n\n{content}")
            return

        # ── Non-command messages → save to inbox ──
        is_command = bool(text.strip().startswith("/"))
        if not is_command:
            inbox_item = _store_inbox_item(db, telegram_user_id, chat_id, message)
            _send_text(client, base_url, chat_id, f"Saved to inbox #{inbox_item.id} ({inbox_item.item_type}).")
            return

        # ── /note add ──
        if lowered.startswith("/note add "):
            content = text[10:].strip()
            if not content:
                _send_text(client, base_url, chat_id, "Usage: /note add <content>")
                return
            now = datetime.utcnow()
            note = models.EncryptedNote(title="", cipher_text=encrypt_text(content), created_at=now, updated_at=now)
            db.add(note)
            db.commit()
            _send_text(client, base_url, chat_id, f"Saved encrypted note #{note.id}")
            return

        # ── /note list ──
        if lowered.startswith("/note list"):
            notes = db.query(models.EncryptedNote).order_by(models.EncryptedNote.updated_at.desc()).limit(10).all()
            if not notes:
                _send_text(client, base_url, chat_id, "No notes yet.")
                return
            lines = ["Latest notes:"]
            for n in notes:
                try:
                    content = decrypt_text(n.cipher_text)
                except Exception:
                    content = "<decrypt-error>"
                lines.append(f"#{n.id}: {content[:60].replace(chr(10), ' ')}")
            lines.append("Reply with #<id> or use /note read <id> for full text.")
            _send_text(client, base_url, chat_id, "\n".join(lines))
            return

        # ── /task add ──
        if lowered.startswith("/task add "):
            title = text[10:].strip()
            if not title:
                _send_text(client, base_url, chat_id, "Usage: /task add <title>")
                return
            now = datetime.utcnow()
            task = models.Task(title=title, status="todo", priority="medium", updated_at=now)
            db.add(task)
            db.commit()
            _send_text(client, base_url, chat_id, f"Task created #{task.id}")
            return

        # ── /task list ──
        if lowered.startswith("/task list"):
            tasks = db.query(models.Task).order_by(models.Task.created_at.desc()).limit(10).all()
            if not tasks:
                _send_text(client, base_url, chat_id, "No tasks yet.")
                return
            lines = ["Latest tasks:"]
            for t in tasks:
                lines.append(f"#{t.id} [{t.status}] {t.title}")
            _send_text(client, base_url, chat_id, "\n".join(lines))
            return

        # ── /task done <id or partial title> ──
        if lowered.startswith("/task done"):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                _send_text(client, base_url, chat_id, "Usage: /task done <id or partial title>")
                return

            arg = parts[2].strip()
            task = None

            # Try numeric ID first.
            if arg.isdigit():
                task = db.query(models.Task).filter(models.Task.id == int(arg)).first()

            # Fall back to fuzzy title match.
            if not task:
                task = (
                    db.query(models.Task)
                    .filter(models.Task.title.ilike(f"%{arg}%"))
                    .filter(models.Task.status != "done")
                    .first()
                )

            if not task:
                _send_text(client, base_url, chat_id, f"Task not found: {arg!r}")
                return

            now = datetime.utcnow()
            task.status = "done"
            task.completed_at = now
            task.updated_at = now
            db.add(task)
            db.commit()
            _send_text(client, base_url, chat_id, f"Task #{task.id} '{task.title}' marked done.")
            return

        # ── /capture list ──
        if lowered.startswith("/capture list"):
            captures = db.query(models.Capture).order_by(models.Capture.created_at.desc()).limit(10).all()
            if not captures:
                _send_text(client, base_url, chat_id, "No captures yet.")
                return
            lines = ["Latest captures:"]
            for c in captures:
                snippet = c.content.replace('\n', ' ')[:60]
                lines.append(f"#{c.id}: {snippet}")
            _send_text(client, base_url, chat_id, "\n".join(lines))
            return

        # ── /capture ──
        if lowered.startswith("/capture "):
            content = text[9:].strip()
            if not content:
                _send_text(client, base_url, chat_id, "Usage: /capture <text>")
                return
            db.add(models.Capture(content=content, url=""))
            db.commit()
            _send_text(client, base_url, chat_id, "Capture saved.")
            return

        # ── /inbox list ──
        if lowered.startswith("/inbox list"):
            items = (
                db.query(models.TelegramInboxItem)
                .filter(models.TelegramInboxItem.telegram_user_id == telegram_user_id)
                .order_by(models.TelegramInboxItem.created_at.desc())
                .limit(8)
                .all()
            )
            if not items:
                _send_text(client, base_url, chat_id, "Inbox is empty.")
                return
            lines = ["Latest inbox items:"]
            for i in items:
                snippet = (i.text or "").replace("\n", " ")[:45]
                lines.append(f"#{i.id} [{i.item_type}] {snippet}")
            _send_text(client, base_url, chat_id, "\n".join(lines))
            return

        # ── /remind ──
        if lowered.startswith("/remind "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                _send_text(client, base_url, chat_id, "Usage: /remind <minutes> <message>")
                return
            try:
                minutes = int(parts[1])
            except Exception:
                _send_text(client, base_url, chat_id, "Minutes must be a number.")
                return
            if minutes < 1:
                _send_text(client, base_url, chat_id, "Minutes must be >= 1.")
                return
            msg = parts[2].strip()
            if not msg:
                _send_text(client, base_url, chat_id, "Message is required.")
                return
            reminder = models.Reminder(
                message=msg,
                channel="telegram",
                target=chat_id,
                remind_at=datetime.utcnow() + timedelta(minutes=minutes),
                is_recurring=False,
                recurrence_minutes=None,
                status="pending",
            )
            db.add(reminder)
            db.commit()
            _send_text(client, base_url, chat_id, f"Reminder scheduled in {minutes} minute(s).")
            return

        # ── /reminder list ──
        if lowered.startswith("/reminder list"):
            reminders = (
                db.query(models.Reminder)
                .order_by(models.Reminder.remind_at.asc())
                .limit(10)
                .all()
            )
            if not reminders:
                _send_text(client, base_url, chat_id, "No reminders yet.")
                return
            lines = ["Upcoming reminders:"]
            for r in reminders:
                lines.append(f"#{r.id} [{r.status}] {r.remind_at.isoformat()} - {r.message[:50]}")
            _send_text(client, base_url, chat_id, "\n".join(lines))
            return

        # ── /summary ──
        if lowered.startswith("/summary"):
            summary = get_today_summary(db)
            _send_text(
                client, base_url, chat_id,
                "Today summary:\n"
                f"Captures: {summary.captures_today}\n"
                f"Open tasks: {summary.tasks_open}\n"
                f"Done today: {summary.tasks_done_today}\n"
                f"Pending reminders: {summary.reminders_pending}\n"
                f"Sent today: {summary.reminders_sent_today}",
            )
            return

        _send_text(client, base_url, chat_id, "Unknown command. Use /help")
    finally:
        db.close()
