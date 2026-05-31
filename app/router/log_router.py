"""
log_router.py
Visitor logging endpoints — log-visitor, log-skip, contact-outreach.

Rate limiting:
  /log-visitor  → email limiter (hr only)  — triggers AI + email pipeline
  /log-skip     → general limiter          — simple write, no AI
  /contact-outreach → general limiter      — GitHub/LinkedIn calls, no AI
"""

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.models.log_model import ContactInfo, User
from app.services.email import generate_email_from_prompt, send_email_background
from app.services.outreach import connect_on_linkedin, follow_on_github
from app.services.portfolio import build_future_opportunity_prompt, build_role_aware_prompt
from app.services.sheets import sheet_append, sheet_update_contact
from app.settings.config import get_settings
from app.utils.excel_manager import ExcelManager
from app.utils.rate_limiter import RateLimiter

logger   = logging.getLogger("portfolio.logs")
settings = get_settings()
router   = APIRouter(tags=["logs"])

excel            = ExcelManager("/backend/logs/visitors.xlsx")
_email_limiter   = RateLimiter.for_email()
_general_limiter = RateLimiter.for_general()


# ── Private helper ─────────────────────────────────────────────────────────
def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

# Add this helper function above the route
def _generate_and_send_email(
    name: str,
    role: str,
    company: str,
    answers: str,
    is_hiring: bool,
    email: str,
):
    """
    Runs entirely in background after response is sent.
    Generates AI email and delivers it — user never waits for this.
    """
    from app.services.email import generate_email_from_prompt, _send
    from app.services.portfolio import build_role_aware_prompt, build_future_opportunity_prompt

    prompt = (
        build_role_aware_prompt(name, role, company, answers)
        if is_hiring
        else build_future_opportunity_prompt(name, role, company)
    )
    subject, body, model_used = generate_email_from_prompt(prompt)
    _send(email, subject, body)
    logger.info(f"Background email sent to {email} via {model_used}")
    return subject, body, model_used

# ── Routes ─────────────────────────────────────────────────────────────────
@router.post("/log-visitor")
def log_visitor(
    data: User,
    request: Request,
    background_tasks: BackgroundTasks,
    limiter: RateLimiter = Depends(lambda: _email_limiter),
):
    ip = _get_client_ip(request)

    if data.userType == "hr" and not limiter.is_allowed(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many email requests. Please wait 10 minutes before trying again.",
        )

    user_id = str(uuid4())
    ip      = _get_client_ip(request)

    # Build the row with empty subject/body/model — they get filled in background
    row = [
        user_id,
        data.name,
        data.email,
        data.userType,
        data.company,
        data.answers,
        f"{data.userType.capitalize()} Logged",
        data.role,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "",   # subject  — filled by background task
        "",   # body     — filled by background task
        "",   # github
        "",   # linkedin
        "",   # model_used — filled by background task
        "portfolio",
        ip,
    ]

    # Log visitor row immediately
    def _write_excel(r: list):
        try:
            excel.append_visitor(r)
            logger.info(f"Excel write succeeded for {data.email}")
        except Exception as e:
            logger.warning(f"Excel write failed — Sheets is fallback. Error: {e}")

    def _write_sheets(r: list):
        try:
            sheet_append(r)
            logger.info(f"Sheets write succeeded for {data.email}")
        except Exception as e:
            logger.error(f"Sheets write failed. Error: {e}")

    background_tasks.add_task(_write_excel, row)
    background_tasks.add_task(_write_sheets, row)

    # Queue email generation + delivery as background task — never blocks response
    if data.userType == "hr":
        background_tasks.add_task(
            _generate_and_send_email,
            data.name,
            data.role or "Hiring Manager",
            data.company,
            data.answers,
            data.isHiring or False,
            data.email,
        )

    logger.info(f"Visitor logged: {data.email} ({data.userType}) from {ip}")
    return {"status": "ok", "userType": data.userType}

@router.post("/log-skip")
def log_skip(
    request: Request,
    background_tasks: BackgroundTasks,
    limiter: RateLimiter = Depends(lambda: _general_limiter),
):
    ip = _get_client_ip(request)

    if not limiter.is_allowed(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down.",
        )

    row = [
        str(uuid4()), "anonymous", "", "skipped",
        "", "", "Skipped", "",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "", "", "", "", "", "portfolio", ip,
    ]

    def _write_excel(r: list):
        try:
            excel.append_visitor(r)
        except Exception as e:
            logger.warning(f"Excel write failed for skip — Sheets is fallback. Error: {e}")

    def _write_sheets(r: list):
        try:
            sheet_append(r)
        except Exception as e:
            logger.error(f"Sheets write failed for skip. Error: {e}")

    background_tasks.add_task(_write_excel, row)
    background_tasks.add_task(_write_sheets, row)

    logger.info(f"Visitor skipped from {ip}")
    return {"status": "ok"}


@router.post("/contact-outreach")
def contact_outreach(
    info: ContactInfo,
    request: Request,
    background_tasks: BackgroundTasks,
    limiter: RateLimiter = Depends(lambda: _general_limiter),
):
    ip = _get_client_ip(request)

    if not limiter.is_allowed(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down.",
        )

    name     = info.name.strip()
    github   = info.github.strip()
    linkedin = info.linkedin.strip()

    email, name_from_sheet = excel.get_latest_email()
    if not email:
        logger.warning("No valid email found for outreach")
        return {"status": "failed", "reason": "No email available"}

    if not name or name.lower() == "string":
        name = name_from_sheet or "Visitor"

    def _update_excel():
        try:
            excel.update_contact(email, github, linkedin)
        except Exception as e:
            logger.warning(f"Excel update_contact failed — Sheets is fallback. Error: {e}")

    def _update_sheets():
        try:
            sheet_update_contact(email, github, linkedin)
        except Exception as e:
            logger.error(f"Sheets update_contact failed. Error: {e}")

    background_tasks.add_task(_update_excel)
    background_tasks.add_task(_update_sheets)

    email_sent         = False
    github_followed    = False
    linkedin_connected = False

    if not github and not linkedin:
        subject = "Excited to connect!"
        body    = (
            f"Hi {name}, thanks for reaching out! Mohammed's portfolio is designed to engage, "
            f"adapt, and respond with clarity and purpose. Whether you're exploring his work or "
            f"looking to collaborate, you're always welcome here.\n\n"
            f"You can view Mohammed's resume here: {settings.resume_link}"
        )
        send_email_background(background_tasks, email, subject, body)
        email_sent = True

    if github:
        background_tasks.add_task(follow_on_github, github)
        github_followed = True

    if linkedin:
        background_tasks.add_task(connect_on_linkedin, name, email)
        linkedin_connected = True

    logger.info(
        f"Outreach complete for {name}: "
        f"email={email_sent}, gh={github_followed}, li={linkedin_connected}"
    )
    return {
        "status":             "outreach triggered",
        "email_sent":         email_sent,
        "github_followed":    github_followed,
        "linkedin_connected": linkedin_connected,
    }