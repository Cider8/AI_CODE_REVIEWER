"""Outgoing email, behind one switch (settings.email_provider):

- "log":   print the message to the server log (local development)
- "brevo": Brevo's transactional email API over HTTPS. Works on hosts that
           block outbound SMTP ports (e.g. Render's free plan)
- "smtp":  any SMTP server, e.g. a Gmail app password, or Amazon SES's SMTP
           interface once deployed on AWS. Moving providers is config only.

smtplib is blocking, so SMTP sends run in a worker thread to keep the event
loop free.
"""

import asyncio
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr

import httpx

from app.config import settings

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"
SEND_TIMEOUT_SECONDS = 20


def _provider() -> str:
    return (settings.email_provider or "").strip().lower()


def email_enabled() -> bool:
    provider = _provider()
    if provider == "log":
        return True
    if provider == "brevo":
        return bool(settings.brevo_api_key and settings.email_from)
    if provider == "smtp":
        return bool(settings.smtp_host and settings.email_from)
    return False


def _send_smtp_blocking(to: str, subject: str, text: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)

    if settings.smtp_use_ssl:
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=SEND_TIMEOUT_SECONDS)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=SEND_TIMEOUT_SECONDS)
        server.starttls()
    with server:
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password or "")
        server.send_message(msg)


async def _send_brevo(to: str, subject: str, text: str) -> None:
    sender_name, sender_email = parseaddr(settings.email_from or "")
    async with httpx.AsyncClient(timeout=SEND_TIMEOUT_SECONDS) as client:
        response = await client.post(
            BREVO_SEND_URL,
            headers={"api-key": settings.brevo_api_key, "accept": "application/json"},
            json={
                "sender": {"name": sender_name or "KrishnaLens", "email": sender_email},
                "to": [{"email": to}],
                "subject": subject,
                "textContent": text,
            },
        )
    response.raise_for_status()


async def send_email(to: str, subject: str, text: str) -> None:
    provider = _provider()
    if provider == "log":
        print(f"[email:log] to={to} subject={subject!r}\n{text}")
    elif provider == "brevo":
        await _send_brevo(to, subject, text)
    elif provider == "smtp":
        await asyncio.to_thread(_send_smtp_blocking, to, subject, text)
    else:
        raise RuntimeError("Email is not configured (EMAIL_PROVIDER is empty)")


async def send_password_reset_code(to: str, name: str, code: str, minutes: int) -> None:
    await send_email(
        to,
        "Your KrishnaLens password reset code",
        f"Hi {name},\n\n"
        f"Your KrishnaLens password reset code is: {code}\n\n"
        f"It expires in {minutes} minutes and can only be used once.\n"
        "If you didn't ask to reset your password, you can ignore this email; "
        "your password has not been changed.\n\n"
        "— KrishnaLens",
    )
