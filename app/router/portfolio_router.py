"""
portfolio_router.py

Public GET endpoints — frontend reads portfolio data from here.
Admin PUT/POST/DELETE endpoints — JWT protected, admin manages content.

Public endpoints:
  GET /portfolio/all                              → everything in one call
  GET /portfolio/skills                           → skills with icons
  GET /portfolio/projects                         → projects for ChromaGrid
  GET /portfolio/achievements                     → achievements list
  GET /portfolio/publications                     → publications for bento grid
  GET /portfolio/experience                       → experience for timeline
  GET /portfolio/about                            → personal info

Admin endpoints:
  PUT    /admin/portfolio/{section}               → replace full section
  POST   /admin/portfolio/{section}               → add single item to list
  DELETE /admin/portfolio/{section}/{item_id}     → delete item by id
  POST   /admin/portfolio/skills/{category}       → add skill to category
  DELETE /admin/portfolio/skills/{category}/{skill} → remove skill from category
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Any

from app.router.admin_router import verify_token
from app.utils.portfolio_store import (
    add_item,
    add_skill,
    delete_item,
    delete_skill,
    read,
    write,
)

logger = logging.getLogger("portfolio.router")
router = APIRouter()

# Sections that exist as YAML files
VALID_SECTIONS = {
    "skills",
    "projects",
    "achievements",
    "publications",
    "about",
    "experience",
}

# Only list sections support add/delete item operations
# "skills" and "about" are handled separately
LIST_SECTIONS = {
    "projects",
    "achievements",
    "publications",
    "experience",
}


# ── Public endpoints ───────────────────────────────────────────────────────

@router.get("/portfolio/all")
def get_all():
    """
    Single call returns all portfolio data.
    Frontend fetches this once on load — no need for 6 separate calls.

    Response:
    {
        "skills":        { "Languages": [...], "Frontend": [...], ... },
        "projects":      [...],
        "achievements":  [...],
        "publications":  [...],
        "experience":    [...],
        "about":         { "name": "...", "title": "...", ... }
    }
    """
    return {
        "skills":       read("skills"),
        "projects":     read("projects"),
        "achievements": read("achievements"),
        "publications": read("publications"),
        "experience":   read("experience"),
        "about":        read("about"),
    }


@router.get("/portfolio/skills")
def get_skills():
    """
    Returns skills grouped by category, each with name and icon.

    Response:
    {
        "Languages": [
            {"name": "Python", "icon": "https://..."},
            ...
        ],
        ...
    }
    """
    return read("skills")


@router.get("/portfolio/projects")
def get_projects():
    """
    Returns projects list for ChromaGrid component.

    Response:
    [
        {
            "id": "1",
            "image": "/projects/Autism.jpeg",
            "title": "Web-EmoRec",
            "subtitle": "Real-Time Emotion Recognition • ML • OpenCV",
            "handle": "@Im-Mohammed/Web-EmoRec",
            "borderColor": "#ff66cc",
            "gradient": "linear-gradient(135deg, #ff66cc, #000)",
            "url": "https://github.com/..."
        },
        ...
    ]
    """
    return read("projects")


@router.get("/portfolio/achievements")
def get_achievements():
    """
    Returns achievements list.

    Response:
    [
        {"id": "1", "title": "CCNA Certifications"},
        ...
    ]
    """
    return read("achievements")


@router.get("/portfolio/publications")
def get_publications():
    """
    Returns publications for bento grid component.

    Response:
    [
        {
            "id": "1",
            "image": "/certificates/IJCRT.png",
            "title": "Autism Support System",
            "subtitle": "Published in IJCRT",
            "url": "https://ijcrt.org/..."
        },
        ...
    ]
    """
    return read("publications")


@router.get("/portfolio/experience")
def get_experience():
    """
    Returns experience list for vertical timeline component.

    Response:
    [
        {
            "id": "1",
            "role": "Software Developer",
            "company": "Caalm-ai",
            "location": "Remote",
            "period": "Aug 2025 – Present",
            "description": "..."
        },
        ...
    ]
    """
    return read("experience")


@router.get("/portfolio/about")
def get_about():
    """
    Returns personal info.

    Response:
    {
        "name": "Mohammed Karab Ehtesham",
        "title": "AI & Full Stack Developer",
        "bio": "...",
        "location": "...",
        "email": "...",
        "github": "...",
        "linkedin": "..."
    }
    """
    return read("about")


# ── Admin endpoints ────────────────────────────────────────────────────────


@router.put("/admin/portfolio/{section}")
def replace_section(
    section: str,
    data: Any = Body(...),                # ← accepts any JSON — dict or list
    username: str = Depends(verify_token),
):
    """
    Replace an entire section with new data.

    Use when you want to rewrite the full skills map,
    update the about bio, or bulk-replace any section.

    Body: the full new content — dict for skills/about, list for everything else.
    """
    if section not in VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {sorted(VALID_SECTIONS)}",
        )

    success = write(section, data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write data — check server logs")

    logger.info(f"Admin '{username}' replaced section '{section}'")
    return {"status": "ok", "section": section}


@router.post("/admin/portfolio/{section}")
def add_section_item(
    section: str,
    item: dict,
    username: str = Depends(verify_token),
):
    """
    Add a single item to a list section.
    An ID is auto-generated — do not include one in the body.

    Valid sections: projects, achievements, publications, experience

    Example body for projects:
    {
        "image": "/projects/new.jpeg",
        "title": "New Project",
        "subtitle": "Description • Tech • Stack",
        "handle": "@Im-Mohammed/new-project",
        "borderColor": "#ffffff",
        "gradient": "linear-gradient(135deg, #ffffff, #000)",
        "url": "https://github.com/Im-Mohammed/new-project"
    }

    Example body for experience:
    {
        "role": "Backend Developer",
        "company": "Some Company",
        "location": "Remote",
        "period": "Jan 2026 – Present",
        "description": "What you did..."
    }
    """
    if section not in LIST_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Section '{section}' does not support adding items. "
                   f"Valid sections: {sorted(LIST_SECTIONS)}",
        )

    try:
        created = add_item(section, item)
        logger.info(f"Admin '{username}' added item to '{section}': {item.get('title') or item.get('role', '')}")
        return {"status": "ok", "created": created}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/portfolio/{section}/{item_id}")
def delete_section_item(
    section: str,
    item_id: str,
    username: str = Depends(verify_token),
):
    """
    Delete a single item by ID from a list section.
    Get the ID from the /portfolio/{section} response.

    Valid sections: projects, achievements, publications, experience
    """
    if section not in LIST_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Section '{section}' does not support item deletion. "
                   f"Valid sections: {sorted(LIST_SECTIONS)}",
        )

    deleted = delete_item(section, item_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Item '{item_id}' not found in '{section}'",
        )

    logger.info(f"Admin '{username}' deleted item '{item_id}' from '{section}'")
    return {"status": "ok", "deleted": item_id}


@router.post("/admin/portfolio/skills/{category}")
def add_skill_to_category(
    category: str,
    payload: dict,
    username: str = Depends(verify_token),
):
    """
    Add a skill to an existing or new category in skills.yaml.

    Body:
    {
        "name": "Streamlit",
        "icon": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/streamlit/streamlit-original.svg"
    }
    """
    name = payload.get("name", "").strip()
    icon = payload.get("icon", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="'name' field is required")
    if not icon:
        raise HTTPException(status_code=400, detail="'icon' field is required")

    skill = {"name": name, "icon": icon}

    added = add_skill(category, skill)
    if not added:
        raise HTTPException(
            status_code=409,
            detail=f"Skill '{name}' already exists in category '{category}'",
        )

    logger.info(f"Admin '{username}' added skill '{name}' to '{category}'")
    return {"status": "ok", "category": category, "skill": skill}


@router.delete("/admin/portfolio/skills/{category}/{skill_name}")
def remove_skill_from_category(
    category: str,
    skill_name: str,
    username: str = Depends(verify_token),
):
    """
    Remove a skill by name from a category in skills.yaml.

    Example:
      DELETE /admin/portfolio/skills/Libraries/Streamlit
    """
    deleted = delete_skill(category, skill_name)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Skill '{skill_name}' not found in category '{category}'",
        )

    logger.info(f"Admin '{username}' removed skill '{skill_name}' from '{category}'")
    return {"status": "ok", "category": category, "deleted": skill_name}