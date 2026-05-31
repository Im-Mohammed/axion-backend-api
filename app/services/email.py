"""
email.py
AI email generation (OpenRouter with model fallback)
and provider-aware email delivery.

EMAIL_PROVIDER=resend  → sends via Resend API       (Render hosting)
EMAIL_PROVIDER=gmail   → sends via Gmail SMTP        (SimilieHostie shared hosting)

Public interface — the only function the rest of the app calls:
    send_email_background(background_tasks, to_email, subject, body)

Provider selection is fully internal — nothing outside this file
needs to know or care which provider is active.
"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
import resend
from fastapi import BackgroundTasks

from app.settings.config import EmailProvider, get_settings

logger   = logging.getLogger("portfolio.email")
settings = get_settings()

# Builds the priority list at startup, skips any model not set in .env
# Build priority list at startup — skip any not configured in .env
MODEL_PRIORITY = [
    m for m in [settings.model_e1, settings.model_e2, settings.model_e3]
    if m.strip()
]

def _fallback_email() -> tuple[str, str, str]:
    return (
        "Let's stay connected",
        f"Hi, thank you for reaching out. "
        f"You can view Mohammed's resume here: {settings.resume_link}",
        "fallback",
    )


def generate_email_from_prompt(prompt: str) -> tuple[str, str, str]:
    """
    Try each model in MODEL_PRIORITY order.
    Returns (subject, body, model_used).
    Falls back to a static message if no models are configured or all fail.
    """
    if not MODEL_PRIORITY:
        logger.error("No email models configured — set MODEL_E1, MODEL_E2, MODEL_E3 in .env")
        return _fallback_email()

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type":  "application/json",
    }

    for model_name in MODEL_PRIORITY:
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={
                    "model":    model_name,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            result = resp.json()

            choices = result.get("choices")
            if not choices:
                raise ValueError(f"No choices from {model_name}")

            content = choices[0]["message"]["content"]
            lines   = content.strip().split("\n")
            subj_ln = next((l for l in lines if l.lower().startswith("subject:")), None)
            subject = subj_ln.replace("Subject:", "").strip() if subj_ln else "Let's stay connected"
            body    = "\n".join(
                l for l in lines
                if not l.lower().startswith("subject:") and l.strip()
            ).strip()
            body += f"\n\nYou can view Mohammed's resume here: {settings.resume_link}"

            logger.info(f"Email generated via {model_name}")
            return subject, body, model_name

        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")

    logger.error("All AI models failed — using fallback email")
    return _fallback_email()

# ── Provider: Resend ───────────────────────────────────────────────────────
def _send_via_resend(to_email: str, subject: str, body: str):
    """
    Deliver via Resend API.
    Requires in .env:
        RESEND_API_KEY=re_xxxxxxxxxxxx
        RESEND_SENDER=onboarding@yourdomain.com
    """
    try:
        resend.api_key = settings.resend.resend_api_key
        resend.Batch.send([{
            "from":    settings.resend.resend_sender,
            "to":      [to_email],
            "subject": subject,
            "html":    f"<p>{body.replace(chr(10), '<br>')}</p>",
        }])
        logger.info(f"[Resend] Email sent to {to_email}")
    except Exception as e:
        logger.error(f"[Resend] Failed: {e}")


# ── Provider: Gmail ────────────────────────────────────────────────────────
def _send_via_gmail(to_email: str, subject: str, body: str):
    """
    Deliver via Gmail SMTP with STARTTLS.
    Requires in .env:
        EMAIL_USER=mohammedkarabehtesham@gmail.com
        EMAIL_PASS=xxxx xxxx xxxx xxxx  ← Gmail App Password, NOT your login password
        EMAIL_HOST=smtp.gmail.com       ← optional, this is the default
        EMAIL_PORT=587                  ← optional, this is the default

    How to get an App Password:
        Google Account → Security → 2-Step Verification (enable)
        → App Passwords → create → copy the 16-char password
    """
    email_user = settings.email.email_user
    email_pass = settings.email.email_pass

    if not email_user or not email_pass:
        logger.error(
            "[Gmail] EMAIL_USER or EMAIL_PASS not configured — "
            "cannot send email. Check your .env file."
        )
        return

    try:
        # Build MIME message with plain text + HTML alternative
        msg            = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = email_user
        msg["To"]      = to_email

        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(
            f"<p>{body.replace(chr(10), '<br>')}</p>",
            "html",
        ))

        # Connect on port 587, upgrade to TLS via STARTTLS
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.email.email_host, settings.email.email_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(email_user, email_pass)
            server.sendmail(email_user, to_email, msg.as_string())

        logger.info(f"[Gmail] Email sent to {to_email}")

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "[Gmail] Authentication failed. "
            "EMAIL_PASS must be a Gmail App Password, not your account password. "
            "Generate one at: https://myaccount.google.com/apppasswords"
        )
    except smtplib.SMTPException as e:
        logger.error(f"[Gmail] SMTP error: {e}")
    except Exception as e:
        logger.error(f"[Gmail] Unexpected error: {e}")


# ── Provider dispatcher ────────────────────────────────────────────────────
def _send(to_email: str, subject: str, body: str):
    """
    Reads EMAIL_PROVIDER and routes to the correct sending function.
    This is the only place in the codebase that knows about providers.
    """
    if settings.email_provider == EmailProvider.GMAIL:
        _send_via_gmail(to_email, subject, body)
    else:
        _send_via_resend(to_email, subject, body)


# ── Public interface ───────────────────────────────────────────────────────
def send_email_background(
    background_tasks: BackgroundTasks,
    to_email: str,
    subject: str,
    body: str,
):
    """
    The only function the rest of the app calls.

    Queues email delivery as a background task so the HTTP response
    never waits for it. Provider selection happens inside _send().

    Usage (identical regardless of provider):
        send_email_background(background_tasks, data.email, subject, body)
    """
    background_tasks.add_task(_send, to_email, subject, body)