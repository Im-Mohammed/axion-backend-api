from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional
import re


# ── Pydantic models ────────────────────────────────────────────────────────
class User(BaseModel):
    name:     str
    email:    str
    userType: str
    company:  str = ""
    role:     str = ""
    answers:  str = ""
    isHiring: Optional[bool] = None

    @field_validator("name")
    def no_script_in_name(cls, v):
        if re.search(r"[<>\"']", v):
            raise ValueError("Invalid characters in name")
        return v.strip()[:100]

    @field_validator("email")
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()[:200]

    @field_validator("userType")
    def allowed_user_types(cls, v):
        if v not in ("hr", "developer", "visitor"):
            raise ValueError("Invalid userType")
        return v

    @field_validator("answers", "company", "role")
    def sanitize_text(cls, v):
        return v.strip()[:500] if v else ""


class ContactInfo(BaseModel):
    name:     str
    github:   str = ""
    linkedin: str = ""

    @field_validator("github", "linkedin")
    def no_full_urls(cls, v):
        # Accept only usernames, not full URLs
        return re.sub(r"https?://[^/]+/?", "", v).strip("/").strip()[:80]