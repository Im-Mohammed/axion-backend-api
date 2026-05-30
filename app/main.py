from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from datetime import datetime
from uuid import uuid4
from contextlib import asynccontextmanager
from typing import List, Optional
import os
import requests
import resend
import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict

# ── Local modules ──────────────────────────────────────────────────────────
from app.utils.excel_manager import ExcelManager
from app.utils.rate_limiter import RateLimiter
from app.models.log_model import 
# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("portfolio")

# ── Env ────────────────────────────────────────────────────────────────────
load_dotenv()
EMAIL_USER       = os.getenv("EMAIL_USER")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AUTBOUND_API_KEY = os.getenv("AUTBOUND_API_KEY")
GITHUB_TOKEN     = os.getenv("GITHUB_TOKEN")
RESEND_API_KEY   = os.getenv("RESEND_API_KEY")
RESEND_SENDER    = os.getenv("RESEND_SENDER") 
RESUME_LINK      = os.getenv("RESUME_LINK")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")
SHEET_NAME       = os.getenv("SHEET_NAME")
ALLOWED_ORIGINS  = os.getenv("ALLOWED_ORIGINS", "https://www.mohammed-karab.rest").split(",")

# ── Google Sheets (backup) ─────────────────────────────────────────────────
try:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds      = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_PATH, scope)
    gs_client  = gspread.authorize(creds)
    sheet      = gs_client.open(SHEET_NAME).sheet1
    SHEETS_OK  = True
    logger.info("Google Sheets backup connected.")
except Exception as e:
    logger.warning(f"Google Sheets unavailable (backup disabled): {e}")
    SHEETS_OK  = False
    sheet      = None

# ── Excel primary store ────────────────────────────────────────────────────
excel = ExcelManager("logs/visitors.xlsx")

# ── Rate limiter ───────────────────────────────────────────────────────────
limiter = RateLimiter(max_requests=10, window_seconds=60)

# ── Portfolio data ─────────────────────────────────────────────────────────
PORTFOLIO_OVERVIEW = {
    "Skills": {
        "Languages":          ["Python", "JavaScript", "Java", "C++", "C", "R", "Bash"],
        "Frontend":           ["HTML", "CSS", "Bootstrap", "React"],
        "Backend & DevOps":   ["Linux", "Git", "Docker", "Jenkins", "n8n", "Postman", "Heroku", "AWS", "Networking"],
        "Cloud & Deployment": ["GCP", "Render", "Vercel", "GitHub", "InfinityFree"],
        "Security Tools":     ["Nmap", "Hydra", "John The Ripper", "Metasploit", "Burp Suite", "Wireshark", "Kali Linux", "Parrot OS"],
        "Libraries":          ["TensorFlow", "PyTorch", "OpenCV", "NumPy", "Pandas", "LangChain", "LangGraph", "LangSmith", "FastAPI", "Django"],
    },
    "Projects": [
        {"name": "AI-Chemist",              "summary": "Tablet Recognition using Gemini Vision API and Streamlit"},
        {"name": "Healthcare Claims API",   "summary": "RESTful API for medical data using Python"},
        {"name": "Pneumonia Detection",     "summary": "CNN-based X-ray classification for pneumonia detection"},
        {"name": "WebscrapeModel",          "summary": "Django + BeautifulSoup scraper with Excel export"},
        {"name": "Autism Support System",   "summary": "Real-time emotion recognition using ML and OpenCV"},
        {"name": "Mind-Sync",               "summary": "Emotion AI and adaptive learning using TensorFlow"},
    ],
    "Achievements": [
        "CCNA Certifications", "Cybersecurity Essentials", "Gen AI Apps",
        "Prompt Design", "IBM Cybersecurity", "LeetCode 50 Days",
    ],
    "Publications": [
        {"title": "Autism Support System",                 "source": "IJCRT"},
        {"title": "Amazon Sales Analysis",                 "source": "IJIRCCE"},
        {"title": "LLMs From Basics to Practical Understanding", "source": "Medium"},
        {"title": "Dutch National Flag Algorithm",         "source": "Medium"},
    ],
}

skills_str = "; ".join(
    f"{cat}: {', '.join(tools)}"
    for cat, tools in PORTFOLIO_OVERVIEW["Skills"].items()
)
project_lines  = "; ".join(f"{p['name']}: {p['summary']}" for p in PORTFOLIO_OVERVIEW["Projects"])
achievements_str = ", ".join(PORTFOLIO_OVERVIEW["Achievements"])
publications_str = "; ".join(f"{p['title']} ({p['source']})" for p in PORTFOLIO_OVERVIEW["Publications"])



# ── Prompt builders ────────────────────────────────────────────────────────
def build_role_aware_prompt(name: str, role: str, company: str, role_description: str) -> str:
    return f"""
Write a short, warm email from Mohammed Karab Ehtesham to {name}, a {role} at {company},
who is hiring for: "{role_description}".

Mohammed's background includes:
- Skills: {skills_str}
- Projects: {project_lines}
- Achievements: {achievements_str}
- Publications: {publications_str}

The email should:
- Be in first person, from Mohammed
- Mention the company name naturally
- Compare his background to the role
- Highlight relevant skills and projects
- Use a conversational, respectful tone (no "Dear" or formal phrasing)
- Be under 200 words, in 3 short paragraphs
- Return only the subject line (starting with "Subject:") followed by a newline, then the email body
- No headings, markdown, or multiple versions
"""


def build_future_opportunity_prompt(name: str, role: str, company: str) -> str:
    return f"""
Write a short, warm email from Mohammed Karab Ehtesham to {name}, a {role} at {company},
who is not currently hiring.

Mohammed's background:
- Skills: {skills_str}
- Projects: {project_lines}
- Achievements: {achievements_str}
- Publications: {publications_str}

The email should:
- Express admiration for the company's work
- Invite future connection and express interest in being considered for future opportunities
- Show how Mohammed's background aligns with their long-term vision
- Use a conversational, respectful tone (no "Dear" or formal phrasing)
- Be under 150 words, in 2 short paragraphs
- Return only the subject line (starting with "Subject:") followed by a newline, then the email body
- No headings, markdown, or multiple versions
"""


# ── AI email generation with model fallback ────────────────────────────────
MODEL_PRIORITY = [
    "nvidia/nemotron-nano-9b-v2:free",
    "tngtech/deepseek-r1t2-chimera:free",
    "google/gemma-3n-e2b-it:free",
]

def generate_email_from_prompt(prompt: str):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    for model_name in MODEL_PRIORITY:
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
            }
            resp   = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            result = resp.json()
            if "choices" not in result or not result["choices"]:
                raise ValueError(f"No choices from {model_name}")

            content = result["choices"][0]["message"]["content"]
            lines   = content.strip().split("\n")
            subj_ln = next((l for l in lines if l.lower().startswith("subject:")), None)
            subject = subj_ln.replace("Subject:", "").strip() if subj_ln else "Let's stay connected"
            body    = "\n".join(
                l for l in lines if not l.lower().startswith("subject:") and l.strip()
            ).strip()
            body   += f"\n\nYou can view Mohammed's resume here: {RESUME_LINK}"
            logger.info(f"Email generated via {model_name}")
            return subject, body, model_name
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")

    logger.error("All AI models failed — using fallback email")
    return (
        "Let's stay connected",
        f"Hi, thank you for reaching out. You can view Mohammed's resume here: {RESUME_LINK}",
        "fallback",
    )


# ── Resend email utility ───────────────────────────────────────────────────
def send_email_resend(to_email: str, subject: str, body: str):
    try:
        resend.api_key = RESEND_API_KEY
        params: List[resend.Emails.SendParams] = [{
            "from":    RESEND_SENDER,
            "to":      [to_email],
            "subject": subject,
            "html":    f"<p>{body.replace(chr(10), '<br>')}</p>",
        }]
        resend.Batch.send(params)
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Resend failed: {e}")


# ── Sheet helpers (backup writes) ──────────────────────────────────────────
def sheet_append(row: list):
    if not SHEETS_OK:
        return
    try:
        sheet.append_row(row)
    except Exception as e:
        logger.warning(f"Sheet backup append failed: {e}")


def sheet_update_contact(email: str, github: str, linkedin: str):
    if not SHEETS_OK:
        return
    try:
        rows = sheet.get_all_records()
        for i, row in enumerate(rows, start=2):
            if row.get("email") == email:
                if github:
                    sheet.update_cell(i, 12, f"https://github.com/{github}")
                if linkedin:
                    sheet.update_cell(i, 13, f"https://linkedin.com/in/{linkedin}")
                sheet.update_cell(i, 9, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                return
    except Exception as e:
        logger.warning(f"Sheet backup update failed: {e}")


# ── GitHub / LinkedIn outreach ─────────────────────────────────────────────
def follow_on_github(username: str):
    if not username:
        return
    url     = f"https://api.github.com/user/following/{username}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept":        "application/vnd.github+json",
    }
    try:
        r = requests.put(url, headers=headers, timeout=5)
        if r.status_code in (204, 304):
            logger.info(f"GitHub: followed {username}")
        else:
            logger.warning(f"GitHub follow failed ({r.status_code})")
    except Exception as e:
        logger.error(f"GitHub follow error: {e}")


def connect_on_linkedin(name: str, email: str):
    if not name:
        return
    headers = {"X-API-KEY": AUTBOUND_API_KEY, "Content-Type": "application/json"}
    contact_email = email or f"{name.lower().replace(' ', '')}@example.com"
    data = {
        "contactEmail":  contact_email,
        "userEmail":     EMAIL_USER,
        "contentType":   "connectionRequest",
    }
    try:
        requests.post(
            "https://api.autobound.ai/api/external/generate-content/v1",
            headers=headers,
            json=data,
            timeout=5,
        )
        logger.info(f"LinkedIn outreach triggered for {name}")
    except Exception as e:
        logger.error(f"LinkedIn outreach failed: {e}")


# ── App lifespan ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Portfolio API starting up.")
    yield
    logger.info("Portfolio API shutting down.")


# ── FastAPI app ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Mohammed Karab Portfolio API",
    docs_url=None,       # disable Swagger in production
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["mohammed-karab.rest", "www.mohammed-karab.rest", "localhost"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]    = "nosniff"
    response.headers["X-Frame-Options"]           = "DENY"
    response.headers["X-XSS-Protection"]          = "1; mode=block"
    response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response

# Rate limit middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    if not limiter.is_allowed(client_ip):
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})
    return await call_next(request)


# ── Chatbot router ─────────────────────────────────────────────────────────
from backend.app.chatbot.router import router as chatbot_router
app.include_router(chatbot_router)


# ── Admin router ───────────────────────────────────────────────────────────
from backend.app.router.admin_router import router as admin_router
app.include_router(admin_router)


# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/log-visitor")
def log_user(data: User, request: Request):
    user_id    = str(uuid4())
    model_used = ""
    subject    = ""
    body       = ""

    if data.userType == "hr":
        if data.isHiring:
            prompt = build_role_aware_prompt(data.name, data.role or "Hiring Manager", data.company, data.answers)
        else:
            prompt = build_future_opportunity_prompt(data.name, data.role or "Hiring Manager", data.company)
        subject, body, model_used = generate_email_from_prompt(prompt)
        send_email_resend(data.email, subject, body)

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
        subject,
        body,
        "",            # github
        "",            # linkedin
        model_used,
        "portfolio",   # source
        request.client.host,  # ip (for admin visibility)
    ]

    # Primary: Excel
    excel.append_visitor(row)

    # Backup: Google Sheets (non-blocking — if it fails, we continue)
    sheet_append(row)

    logger.info(f"Visitor logged: {data.email} ({data.userType})")
    return {"redirect": "https://mohammed-karab.rest/"}


@app.post("/contact-outreach")
def contact_outreach(info: ContactInfo):
    name    = info.name.strip()
    github  = info.github.strip()
    linkedin = info.linkedin.strip()

    email, name_from_sheet = excel.get_latest_email()
    if not email:
        logger.warning("No valid email found for outreach")
        return {"status": "failed", "reason": "No email available"}

    if not name or name.lower() == "string":
        name = name_from_sheet or "Visitor"

    excel.update_contact(email, github, linkedin)
    sheet_update_contact(email, github, linkedin)

    email_sent       = False
    github_followed  = False
    linkedin_connected = False

    if not github and not linkedin:
        subject = "Excited to connect!"
        body    = (
            f"Hi {name}, thanks for reaching out! Mohammed's portfolio is designed to engage, "
            f"adapt, and respond with clarity and purpose. Whether you're exploring his work or "
            f"looking to collaborate, you're always welcome here.\n\n"
            f"You can view Mohammed's resume here: {RESUME_LINK}"
        )
        send_email_resend(email, subject, body)
        email_sent = True

    if github:
        follow_on_github(github)
        github_followed = True

    if linkedin:
        connect_on_linkedin(name, email)
        linkedin_connected = True

    logger.info(f"Outreach complete for {name}: email={email_sent}, gh={github_followed}, li={linkedin_connected}")
    return {
        "status":            "outreach triggered",
        "email_sent":        email_sent,
        "github_followed":   github_followed,
        "linkedin_connected": linkedin_connected,
    }