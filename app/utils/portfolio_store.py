"""
portfolio_store.py
Reads and writes portfolio YAML data files.
Thread-safe via Lock.

All data lives in /backend/app/data/*.yaml
Comments in YAML files are preserved on manual edits
but stripped on programmatic writes (yaml.dump doesn't preserve comments).
"""

import logging
from pathlib import Path
from threading import Lock
from uuid import uuid4

import yaml

logger    = logging.getLogger("portfolio.store")
_DATA_DIR = Path(__file__).parent.parent / "data"
_lock     = Lock()


def _path(section: str) -> Path:
    return _DATA_DIR / f"{section}.yaml"


def read(section: str) -> dict | list:
    """Read a section from its YAML file."""
    path = _path(section)
    if not path.exists():
        logger.warning(f"Data file not found: {path}")
        return {} if section in ("about", "skills") else []
    try:
        with _lock:
            content = path.read_text(encoding="utf-8")
            return yaml.safe_load(content) or {}
    except Exception as e:
        logger.error(f"Failed to read {section}: {e}")
        return {}


def write(section: str, data: dict | list) -> bool:
    """Overwrite a section's YAML file."""
    path = _path(section)
    try:
        with _lock:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(
                    data,
                    f,                        # write directly to file object
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        logger.info(f"Portfolio section '{section}' updated.")
        return True
    except Exception as e:
        logger.error(f"Failed to write {section}: {e}")
        return False

def add_item(section: str, item: dict) -> dict:
    """Add a single item to a list section."""
    data = read(section)
    if not isinstance(data, list):
        raise ValueError(f"Section '{section}' is not a list")
    item["id"] = str(uuid4())[:8]
    data.append(item)
    write(section, data)
    return item


def delete_item(section: str, item_id: str) -> bool:
    """Delete a single item by ID from a list section."""
    data = read(section)
    if not isinstance(data, list):
        raise ValueError(f"Section '{section}' is not a list")
    original_len = len(data)
    data = [item for item in data if str(item.get("id")) != str(item_id)]
    if len(data) == original_len:
        return False
    write(section, data)
    return True


def add_skill(category: str, skill: dict) -> bool:
    """Add a skill object {name, icon} to a category."""
    skills = read("skills")
    if not isinstance(skills, dict):
        return False
    if category not in skills:
        skills[category] = []
    # Check if skill name already exists in this category
    existing_names = [s.get("name") for s in skills[category] if isinstance(s, dict)]
    if skill.get("name") in existing_names:
        return False
    skills[category].append(skill)
    write("skills", skills)
    return True


def delete_skill(category: str, skill_name: str) -> bool:
    """Remove a skill by name from a category."""
    skills = read("skills")
    if not isinstance(skills, dict):
        return False
    if category not in skills:
        return False
    original_len = len(skills[category])
    skills[category] = [
        s for s in skills[category]
        if not (isinstance(s, dict) and s.get("name") == skill_name)
    ]
    if len(skills[category]) == original_len:
        return False
    write("skills", skills)
    return True

