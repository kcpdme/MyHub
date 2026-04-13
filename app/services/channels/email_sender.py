"""Email channel sender.

Sends plain-text emails via SMTP with STARTTLS or SSL.
Configure via environment variables:
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, SMTP_USE_TLS
"""
from __future__ import annotations

import smtplib
import ssl
from email.mime.text import MIMEText

from app.config import settings


def send_email(target: str, message: str, subject: str = "Automation Hub Reminder") -> tuple[bool, str]:
    """Send a plain-text email to `target` email address.

    Returns (success, detail_message).
    """
    if not settings.smtp_host:
        return False, "SMTP host is not configured (SMTP_HOST)"
    if not settings.smtp_user or not settings.smtp_pass:
        return False, "SMTP credentials are not configured (SMTP_USER / SMTP_PASS)"

    from_addr = settings.smtp_from or settings.smtp_user

    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = target

    try:
        context = ssl.create_default_context()
        if settings.smtp_use_tls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.login(settings.smtp_user, settings.smtp_pass)
                smtp.sendmail(from_addr, [target], msg.as_string())
        else:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=15) as smtp:
                smtp.login(settings.smtp_user, settings.smtp_pass)
                smtp.sendmail(from_addr, [target], msg.as_string())

        return True, f"Email sent to {target}"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed — check SMTP_USER and SMTP_PASS"
    except smtplib.SMTPException as exc:
        return False, f"SMTP error: {exc}"
    except Exception as exc:
        return False, f"Email send failed: {exc}"
