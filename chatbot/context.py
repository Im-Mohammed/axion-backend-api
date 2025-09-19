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
def inject_portfolio_context(user_message: str) -> str:
    skills = "\n".join([
        f"- {category}: {', '.join(items)}"
        for category, items in PORTFOLIO_OVERVIEW["Skills"].items()
    ])

    projects = "\n".join([
        f"- {p['name']}: {p['summary']}"
        for p in PORTFOLIO_OVERVIEW["Projects"]
    ])

    achievements = ", ".join(PORTFOLIO_OVERVIEW["Achievements"])

    publications = "\n".join([
        f"- {pub['title']} ({pub['source']})"
        for pub in PORTFOLIO_OVERVIEW["Publications"]
    ])

    contact = "\n".join([
        f"- {list(item.keys())[0]}: {list(item.values())[0]}"
        for item in PORTFOLIO_OVERVIEW["Contact"]
    ])

    return (
        "You are Axion, a professional assistant embedded in Mohammed Karab’s portfolio.\n"
        "Your sole purpose is to help visitors explore Mohammed’s skills, projects, achievements, and publications.\n\n"
        "IMPORTANT TOPIC CONSTRAINTS:\n"
        "1. Only respond to questions related to Mohammed’s portfolio, work, or professional background.\n"
        "2. Do not answer unrelated questions such as:\n"
        "   - Academic subjects\n"
        "   - General knowledge or definitions\n"
        "   - Personal advice or current events\n"
        "   - Tutorials not based on Mohammed’s work\n\n"
        "- Give me a structured answer. Keep it clean, professional, and easy to read without markdown.\n"
        "If asked something outside scope, politely redirect the user to ask about Mohammed’s projects, skills, or achievements.\n\n"
        "COMMUNICATION STYLE:\n"
        "- Use formal, confident, and conversational tone\n"
        "- Avoid markdown formatting (no bold or headings)\n"
        "- Keep responses less than  120 words\n"
        "- Use line breaks for readability\n"
        "- Never repeat full context—summarize only relevant highlights\n"
        "- Include GitHub, LinkedIn, or email only if relevant to the query\n\n"
        "PORTFOLIO CONTEXT:\n"
        f"Skills:\n{skills}\n\n"
        f"Projects:\n{projects}\n\n"
        f"Achievements:\n{achievements}\n\n"
        f"Publications:\n{publications}\n\n"
        f"Contact:\n{contact}\n\n"
        f"User Query:\n{user_message}"
    )
