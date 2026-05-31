"""
portfolio.py
Static portfolio data and AI prompt builders.
Moved out of main.py — main.py should not know about Mohammed's CV.
"""

from app.settings.config import get_settings

settings = get_settings()

PORTFOLIO_OVERVIEW = {
    "Experience":{
        "Total_Experience"    : "1+ Year of Experience " ,
        "Caalm-ai": {
            "Start" : "October 2025",
            "End"   : "Currently Employed",
            "Title" : "Software Developer",
            "Description": "Worked on various end-to-end project including the frontend and backend."
        },
        "Freelance":{
            "Start" : "June 2025",
            "End"   : " September 2025",
            "Title" : "AI Engineer",
            "Description" : "Assisted the team to automate the workflow of the network using tools like Cyberark, Solarwinds, Azure OpenAPI. "
        }
    },
    "Skills": {
        "Languages":          ["Python", "JavaScript", "Java", "C++", "C", "R", "Bash"],
        "Frontend":           ["HTML", "CSS", "Bootstrap", "React"],
        "Backend & DevOps":   ["Linux", "Git", "Docker", "Jenkins", "n8n", "Postman", "Heroku", "AWS", "Networking"],
        "Cloud & Deployment": ["GCP", "Render", "Vercel", "GitHub", "InfinityFree"],
        "Security Tools":     ["Nmap", "Hydra", "John The Ripper", "Metasploit", "Burp Suite", "Wireshark", "Kali Linux", "Parrot OS"],
        "Libraries":          ["TensorFlow", "PyTorch", "OpenCV", "NumPy", "Pandas", "LangChain", "LangGraph", "LangSmith", "FastAPI", "Django"],
    },
    "Projects": [
        {"name": "AI-Chemist",            "summary": "Tablet Recognition using Gemini Vision API and Streamlit"},
        {"name": "Healthcare Claims API", "summary": "RESTful API for medical data using Python"},
        {"name": "Pneumonia Detection",   "summary": "CNN-based X-ray classification for pneumonia detection"},
        {"name": "WebscrapeModel",        "summary": "Django + BeautifulSoup scraper with Excel export"},
        {"name": "Autism Support System", "summary": "Real-time emotion recognition using ML and OpenCV"},
        {"name": "Mind-Sync",             "summary": "Emotion AI and adaptive learning using TensorFlow"},
    ],
    "Achievements": [
        "CCNA Certifications", "Cybersecurity Essentials", "Gen AI Apps",
        "Prompt Design", "IBM Cybersecurity", "LeetCode 50 Days",
    ],
    "Publications": [
        {"title": "Autism Support System",                  "source": "IJCRT"},
        {"title": "Amazon Sales Analysis",                  "source": "IJIRCCE"},
        {"title": "LLMs From Basics to Practical Understanding", "source": "Medium"},
        {"title": "Dutch National Flag Algorithm",          "source": "Medium"},
    ],
}

# ── Pre-built strings for prompts ──────────────────────────────────────────
skills_str = "; ".join(
    f"{cat}: {', '.join(tools)}"
    for cat, tools in PORTFOLIO_OVERVIEW["Skills"].items()
)
project_lines    = "; ".join(f"{p['name']}: {p['summary']}" for p in PORTFOLIO_OVERVIEW["Projects"])
achievements_str = ", ".join(PORTFOLIO_OVERVIEW["Achievements"])
publications_str = "; ".join(f"{p['title']} ({p['source']})" for p in PORTFOLIO_OVERVIEW["Publications"])
exp = PORTFOLIO_OVERVIEW["Experience"]
experience_str = (
    f"Total Experience: {exp['Total_Experience'].strip()}. "
    f"Currently working as a {exp['Caalm-ai']['Title']} at Caalm-ai since {exp['Caalm-ai']['Start']}, "
    f"{exp['Caalm-ai']['Description'].strip()} "
    f"Previously worked as a {exp['Freelance']['Title']} from {exp['Freelance']['Start']} to {exp['Freelance']['End'].strip()}, "
    f"{exp['Freelance']['Description'].strip()}"
)


def build_role_aware_prompt(name: str, role: str, company: str, role_description: str) -> str:
    return f"""
Write a short, warm email from Mohammed Karab Ehtesham to {name}, a {role} at {company},
who is hiring for: "{role_description}".

Mohammed's background:
- Skills: {skills_str}
- Projects: {project_lines}
- Achievements: {achievements_str}
- Publications: {publications_str}
- Experience :{experience_str}

Rules:
- First person, from Mohammed
- Mention the company name naturally
- Under 200 words, 3 short paragraphs
- Conversational tone — no "Dear"
- Return ONLY: Subject: <line>, then the email body
- No markdown, no multiple versions
"""


def build_future_opportunity_prompt(name: str, role: str, company: str) -> str:
    return f"""
Write a short, warm email from Mohammed Karab Ehtesham to {name}, a {role} at {company},
who is not currently hiring.

Mohammed's background:
- Skills: {skills_str}
- Projects: {project_lines}

Rules:
- Express admiration for the company
- Invite future consideration
- Under 150 words, 2 short paragraphs
- Conversational tone — no "Dear"
- Return ONLY: Subject: <line>, then the email body
- No markdown, no multiple versions
"""