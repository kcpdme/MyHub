from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import SessionLocal
from app.services.crypto_service import decrypt_text, encrypt_text


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

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="telegram-bot-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

        with httpx.Client(timeout=max(settings.telegram_bot_poll_timeout_seconds + 5, 10)) as client:
            while not self._stop_event.is_set():
                try:
                    params = {
                        "timeout": max(settings.telegram_bot_poll_timeout_seconds, 5),
                        "allowed_updates": '["message"]',
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

                        if text and chat_id and telegram_user_id:
                            self._handle_message(client, base_url, chat_id, telegram_user_id, text)
                except Exception:
                    time.sleep(2)

    def _send_text(self, client: httpx.Client, base_url: str, chat_id: str, text: str) -> None:
        client.post(f"{base_url}/sendMessage", json={"chat_id": chat_id, "text": text})

    def _is_allowed_user(self, db: Session, telegram_user_id: str) -> bool:
        return (
            db.query(models.AllowedTelegramUser)
            .filter(models.AllowedTelegramUser.telegram_user_id == telegram_user_id)
            .filter(models.AllowedTelegramUser.is_active.is_(True))
            .first()
            is not None
        )

    def _handle_message(
        self,
        client: httpx.Client,
        base_url: str,
        chat_id: str,
        telegram_user_id: str,
        text: str,
    ) -> None:
        db: Session = SessionLocal()
        try:
            lowered = text.lower()

            if lowered in {"/id", "/whoami"}:
                self._send_text(client, base_url, chat_id, f"telegram_user_id: {telegram_user_id}")
                return

            if lowered in {"/start", "/help"}:
                self._send_text(
                    client,
                    base_url,
                    chat_id,
                    "Commands:\n"
                    "/id\n"
                    "/note add <content>\n"
                    "/note list\n"
                    "/task add <title>\n"
                    "/task list\n"
                    "/capture <text>\n"
                    "/remind <minutes> <message>",
                )
                return

            if not self._is_allowed_user(db, telegram_user_id):
                self._send_text(
                    client,
                    base_url,
                    chat_id,
                    f"Access denied. Ask admin to allow telegram_user_id: {telegram_user_id}",
                )
                return

            if lowered.startswith("/note add "):
                content = text[10:].strip()
                if not content:
                    self._send_text(client, base_url, chat_id, "Usage: /note add <content>")
                    return

                now = datetime.utcnow()
                note = models.EncryptedNote(
                    title="",
                    cipher_text=encrypt_text(content),
                    created_at=now,
                    updated_at=now,
                )
                db.add(note)
                db.commit()
                self._send_text(client, base_url, chat_id, f"Saved encrypted note #{note.id}")
                return

            if lowered.startswith("/note list"):
                notes = db.query(models.EncryptedNote).order_by(models.EncryptedNote.updated_at.desc()).limit(10).all()
                if not notes:
                    self._send_text(client, base_url, chat_id, "No notes yet.")
                    return

                lines: list[str] = ["Latest notes:"]
                for n in notes:
                    try:
                        content = decrypt_text(n.cipher_text)
                    except Exception:
                        content = "<decrypt-error>"
                    snippet = content[:60].replace("\n", " ")
                    lines.append(f"#{n.id}: {snippet}")
                self._send_text(client, base_url, chat_id, "\n".join(lines))
                return

            if lowered.startswith("/task add "):
                title = text[10:].strip()
                if not title:
                    self._send_text(client, base_url, chat_id, "Usage: /task add <title>")
                    return

                task = models.Task(title=title, status="todo", priority="medium")
                db.add(task)
                db.commit()
                self._send_text(client, base_url, chat_id, f"Task created #{task.id}")
                return

            if lowered.startswith("/task list"):
                tasks = db.query(models.Task).order_by(models.Task.created_at.desc()).limit(10).all()
                if not tasks:
                    self._send_text(client, base_url, chat_id, "No tasks yet.")
                    return

                lines = ["Latest tasks:"]
                for t in tasks:
                    lines.append(f"#{t.id} [{t.status}] {t.title}")
                self._send_text(client, base_url, chat_id, "\n".join(lines))
                return

            if lowered.startswith("/capture "):
                content = text[9:].strip()
                if not content:
                    self._send_text(client, base_url, chat_id, "Usage: /capture <text>")
                    return
                db.add(models.Capture(content=content, url=""))
                db.commit()
                self._send_text(client, base_url, chat_id, "Capture saved.")
                return

            if lowered.startswith("/remind "):
                parts = text.split(" ", 2)
                if len(parts) < 3:
                    self._send_text(client, base_url, chat_id, "Usage: /remind <minutes> <message>")
                    return
                try:
                    minutes = int(parts[1])
                except Exception:
                    self._send_text(client, base_url, chat_id, "Minutes must be a number.")
                    return
                if minutes < 1:
                    self._send_text(client, base_url, chat_id, "Minutes must be >= 1.")
                    return

                message = parts[2].strip()
                if not message:
                    self._send_text(client, base_url, chat_id, "Message is required.")
                    return

                reminder = models.Reminder(
                    message=message,
                    channel="telegram",
                    target=chat_id,
                    remind_at=datetime.utcnow() + timedelta(minutes=minutes),
                    is_recurring=False,
                    recurrence_minutes=None,
                    status="pending",
                )
                db.add(reminder)
                db.commit()
                self._send_text(client, base_url, chat_id, f"Reminder scheduled in {minutes} minute(s).")
                return

            self._send_text(client, base_url, chat_id, "Unknown command. Use /help")
        finally:
            db.close()
