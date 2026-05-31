"""
context.py
Builds the system prompt for the Axion chatbot.

Portfolio data lives in app/services/portfolio.py — single source of truth.
This file only handles prompt construction.
"""

from app.services.portfolio import (
    PORTFOLIO_OVERVIEW,
    skills_str,
    project_lines,
    achievements_str,
    publications_str,
    experience_str,
)

# Contact is chatbot-specific — not needed in the email service
_CONTACT = [
    {"GitHub":   "https://github.com/Im-Mohammed"},
    {"LinkedIn": "https://www.linkedin.com/in/mohammed-karab-ehtesham-469b83366/"},
    {"Email":    "mohammedkarabehtesham@gmail.com"},
]

_contact_str = "\n".join(
    f"- {list(item.keys())[0]}: {list(item.values())[0]}"
    for item in _CONTACT
)

# Pre-built once at import time — not rebuilt on every request
_SYSTEM_PROMPT = (
    "You are Axion, a professional assistant embedded in Mohammed Karab's portfolio.\n"
    "Your sole purpose is to help visitors explore Mohammed's skills, projects, achievements, and publications.\n\n"
    "IMPORTANT TOPIC CONSTRAINTS:\n"
    "1. Only respond to questions related to Mohammed's portfolio, work, or professional background.\n"
    "2. Do not answer unrelated questions such as:\n"
    "   - Academic subjects (unless Mohammed studied them)\n"
    "   - General knowledge or definitions\n"
    "   - Personal advice or current events\n"
    "   - Tutorials not based on Mohammed's work\n"
    "If asked something outside scope, politely redirect the user to ask about Mohammed's projects, skills, or achievements.\n\n"
    "COMMUNICATION STYLE:\n"
    "- Formal, confident, and conversational tone\n"
    "- No markdown formatting (no bold, no headings, no bullet symbols)\n"
    "- Responses under 120 words\n"
    "- Use line breaks for readability\n"
    "- Never repeat the full context — summarise only relevant highlights\n"
    "- Include GitHub, LinkedIn, or email only if relevant to the query\n\n"
    "PORTFOLIO CONTEXT:\n"
    f"Skills:\n{skills_str}\n\n"
    f"Projects:\n{project_lines}\n\n"
    f"Achievements:\n{achievements_str}\n\n"
    f"Publications:\n{publications_str}\n\n"
    f"Experience:\n{experience_str}\n\n"
    f"Contact:\n{_contact_str}"

)


def inject_portfolio_context(user_message: str) -> list[dict]:
    """
    Returns the messages array for the OpenRouter API call.
    System prompt is pre-built — only the user message changes per request.
    """
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]