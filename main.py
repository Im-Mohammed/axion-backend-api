from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime
from uuid import uuid4
import os
import requests
import resend
from typing import List
from chatbot.router import router as chatbot_router
from contextlib import asynccontextmanager
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AUTBOUND_API_KEY = os.getenv("AUTBOUND_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_SENDER = os.getenv("RESEND_SENDER")
RESUME_LINK = os.getenv("RESUME_LINK")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")
SHEET_NAME = os.getenv("SHEET_NAME")
DEBUG = True

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_PATH, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open(SHEET_NAME).sheet1

# FastAPI setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.mohammed-karab.rest"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chatbot_router)

# Models
class User(BaseModel):
    name: str
    email: str
    userType: str
    company: str = ""
    role: str = ""
    answers: str = ""

class ContactInfo(BaseModel):
    name: str
    github: str = ""
    linkedin: str = ""

PORTFOLIO_OVERVIEW = {
    "Skills": {
        "Languages": ["Python", "JavaScript", "Java", "C++", "C", "R", "Bash"],
        "Frontend": ["HTML", "CSS", "Bootstrap", "React"],
        "Backend & DevOps": ["Linux", "Git", "Docker", "Jenkins", "n8n", "Postman", "Heroku", "AWS", "Networking"],
        "Cloud & Deployment": ["GCP", "Render", "Vercel", "GitHub", "InfinityFree"],
        "Security Tools": ["Nmap", "Hydra", "John The Ripper", "Metasploit", "Burp Suite", "Wireshark", "Kali Linux", "Parrot OS"],
        "Libraries": ["TensorFlow", "PyTorch", "OpenCV", "NumPy", "Pandas", "LangChain", "LangGraph", "LangSmith", "FastAPI", "Django"]
    },
    "Projects": [
        {"name": "AI-Chemist", "summary": "Tablet Recognition using Gemini Vision API and Streamlit"},
        {"name": "Healthcare Claims API", "summary": "RESTful API for medical data using Python"},
        {"name": "Pneumonia Detection Model", "summary": "CNN-based X-ray classification for pneumonia detection"},
        {"name": "WebscrapeModel", "summary": "Django + BeautifulSoup scraper with Excel export"},
        {"name": "Autism Support System", "summary": "Real-time emotion recognition using ML and OpenCV"},
        {"name": "Mind-Sync", "summary": "Emotion AI and adaptive learning using TensorFlow"}
    ],
    "Achievements": [
        "CCNA Certifications", "Cybersecurity Essentials", "Gen AI Apps", "Prompt Design", "IBM Cybersecurity", "LeetCode 50 Days"
    ],
    "Contact": [
        {"GitHub": "https://github.com/Im-Mohammed"},
        {"LinkedIn": "https://www.linkedin.com/in/mohammed-karab-ehtesham-469b83366/"},
        {"Email": "mohammedkarabehtesham@gmail.com"}
    ],
    "Publications": [
        {"title": "Autism Support System", "source": "IJCRT"},
        {"title": "Amazon Sales Analysis", "source": "IJIRCCE"},
        {"title": "LLMs From Basics to Practical Understanding", "source": "Medium"},
        {"title": "Dutch National Flag Algorithm", "source": "Medium"}
    ]
}

skills_str = "; ".join([
    f"{category}: {', '.join(tools)}"
    for category, tools in PORTFOLIO_OVERVIEW["Skills"].items()
])

project_lines = "; ".join([
    f"{p['name']}: {p['summary']}"
    for p in PORTFOLIO_OVERVIEW["Projects"]
])
achievements_str = ", ".join(PORTFOLIO_OVERVIEW["Achievements"])

publications_str = "; ".join([
    f"{pub['title']} ({pub['source']})"
    for pub in PORTFOLIO_OVERVIEW["Publications"]
])


# Prompt builders
def build_role_aware_prompt(name, role, company, role_description):
    return f"""
You are a professional assistant writing on behalf of Mohammed Karab Ehtesham.

The recipient is {name}, a {role} at {company}.
They are hiring for: "{role_description}"

Mohammed’s skills: {skills_str}
Relevant projects: {project_lines}
Achievements: {achievements_str}
Publications: {publications_str}

Write a concise, emotionally intelligent email that compares Mohammed’s background to the role description. Highlight relevant skills and projects naturally. Mention the company name. Make the email feel human—like it was written by someone who genuinely admires the recipient’s work. Use natural phrasing, subtle warmth, and a conversational tone. Keep it concise—no more than 3 short paragraphs.

Return the subject and body separated by a newline.
"""

def build_future_opportunity_prompt(name, role, company):
    return f"""
You are a professional assistant writing on behalf of Mohammed Karab Ehtesham.

The recipient is {name}, a {role} at {company}.
They are not currently hiring.

Mohammed’s skills: {skills_str}
Relevant projects: {project_lines}
Achievements: {achievements_str}
Publications: {publications_str}

Write a warm, emotionally intelligent email that expresses admiration for the company’s work and invites future connection. Mention how Mohammed’s background aligns with their long-term vision. Make the email feel human—like it was written by someone who genuinely respects the recipient’s work. Use natural phrasing, subtle warmth, and a conversational tone. Keep it concise—no more than 3 short paragraphs.

Return the subject and body separated by a newline.
"""

# Email generation
def generate_email_from_prompt(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        result = response.json()
        content = result["choices"][0]["message"]["content"]

        lines = content.strip().split("\n")
        subject_line = next((line for line in lines if line.lower().startswith("subject:")), None)
        subject = subject_line.replace("Subject:", "").strip() if subject_line else "Let's stay connected"
        body_lines = [line for line in lines if not line.lower().startswith("subject:") and line.strip()]
        body = "\n".join(body_lines).strip()
        resume_note = f"\n\nYou can view Mohammed’s resume here: {RESUME_LINK}"
        return subject, body + resume_note
    except Exception as e:
        print("AI email generation failed:", e)
        fallback_body = f"Hi, thank you for reaching out. You can view Mohammed’s resume here: {RESUME_LINK}"
        return "Let's stay connected", fallback_body

# Resend email utility
def send_email_resend(to_email, subject, body):
    try:
        resend.api_key = RESEND_API_KEY
        params: List[resend.Emails.SendParams] = [{
            "from": RESEND_SENDER,
            "to": [to_email],
            "subject": subject,
            "html": f"<p>{body.replace(chr(10), '<br>')}</p>"
        }]
        resend.Batch.send(params)
        if DEBUG:
            print(f"✅ Email sent via Resend to {to_email}")
    except Exception as e:
        print(f"❌ Resend email failed:", e)

# Log user
@app.post("/log-visitor")
def log_user(data: User):
    user_id = str(uuid4())
    hiring = not data.answers.lower().startswith("not hiring")

    if data.userType == "hr":
        if hiring:
            prompt = build_role_aware_prompt(data.name, data.role or "Hiring Manager", data.company, data.answers)
        else:
            prompt = build_future_opportunity_prompt(data.name, data.role or "Hiring Manager", data.company)
        subject, body = generate_email_from_prompt(prompt)
    else:
        subject = ""
        body = ""

    sheet.append_row([
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
        "", "", "portfolio"
    ])
    return {"redirect": "https://mohammed-karab.rest/"}

# Get latest email
def get_latest_email_from_sheet():
    try:
        rows = sheet.get_all_records()
        for row in reversed(rows):
            email = row.get("email", "")
            name = row.get("name", "")
            if email and "@" in email and not email.lower().startswith("string"):
                print("✅ Found fallback email:", email)
                return email, name
        print("❌ No valid fallback email found")
        return None, None
    except Exception as e:
        print("❌ Sheet read error:", e)
        return None, None

# Log contact
def log_contact_to_sheet(name, email, github, linkedin, source="contact"):
    try:
        rows = sheet.get_all_records()
        updated = False
        for i, row in enumerate(rows, start=2):
            if row.get("email") == email:
                sheet.update_cell(i, 12, f"https://github.com/{github}" if github else row.get("github", ""))
                sheet.update_cell(i, 13, f"https://linkedin.com/in/{linkedin}" if linkedin else row.get("linkedin", ""))
                sheet.update_cell(i, 9, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                sheet.update_cell(i, 14, source)
                updated = True
                break
        if not updated:
            sheet.append_row([
                str(uuid4()), name, email, "", "", "", "", "", datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "", "", f"https://github.com/{github}" if github else "",
                f"https://linkedin.com/in/{linkedin}" if linkedin else "", source
            ])
    except Exception as e:
        print("❌ Sheet write error:", e)

# # Send sheet link
# def send_daily_sheet_link():
#     try:
#         sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet.spreadsheet.id}"
#         subject = f"Daily Visitor Log - {datetime.now().strftime('%d %b %Y')}"
#         body = f"Here’s the latest visitor log: {sheet_url}"
#         send_email_resend(EMAIL_USER, subject, body)
#         if DEBUG:
#             print("✅ Sheet link sent successfully.")
#     except Exception as e:
#         print("❌ Failed to send sheet link:", e)

def follow_on_github(username):
    if not username:
        return
    url = f"https://api.github.com/user/following/{username}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    try:
        response = requests.put(url, headers=headers, timeout=5)
        if response.status_code in [204, 304]:
            print(f"✅ Followed {username} on GitHub")
        else:
            print(f"❌ GitHub follow failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ GitHub follow error:", e)
def connect_on_linkedin(name, email):
    if not name:
        return
    headers = {
        "X-API-KEY": AUTBOUND_API_KEY,
        "Content-Type": "application/json"
    }
    contact_email = email if email else f"{name.lower().replace(' ', '')}@example.com"
    data = {
        "contactEmail": contact_email,
        "userEmail": EMAIL_USER,
        "contentType": "connectionRequest"
    }
    try:
        requests.post("https://api.autobound.ai/api/external/generate-content/v1", headers=headers, json=data, timeout=5)
        print(f"✅ LinkedIn outreach triggered for {name}")
    except Exception as e:
        print(f"❌ LinkedIn outreach failed:", e)
@app.post("/contact-outreach")
def contact_outreach(info: ContactInfo):
    name = info.name.strip()
    github = info.github.strip()
    linkedin = info.linkedin.strip()

    email, name_from_sheet = get_latest_email_from_sheet()
    if not email:
        print("❌ No valid email found in sheet")
        return {"status": "failed", "reason": "No email available"}
    if not name or name.lower() == "string":
        name = name_from_sheet or "Visitor"

    log_contact_to_sheet(name, email, github, linkedin)

    email_sent = False
    if not github and not linkedin:
        subject = "Excited to connect!"
        body = f"Hi {name}, thanks for reaching out! Mohammed’s portfolio is designed to engage, adapt, and respond with clarity and purpose. Whether you're exploring his work or looking to collaborate, you're always welcome here.\n\nYou can view Mohammed’s resume here: {RESUME_LINK}"
        send_email_resend(email, subject, body)
        email_sent = True

    github_followed = False
    if github:
        follow_on_github(github)
        github_followed = True

    linkedin_connected = False
    if linkedin:
        connect_on_linkedin(name, email)
        linkedin_connected = True

    print("✅ Contact flow completed:", {
        "email_sent": email_sent,
        "github_followed": github_followed,
        "linkedin_connected": linkedin_connected
    })

    return {
        "status": "outreach triggered",
        "email_sent": email_sent,
        "github_followed": github_followed,
        "linkedin_connected": linkedin_connected
    }
