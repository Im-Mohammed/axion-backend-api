"""
config.py
Single source of truth for all environment variables.

Structure:
  Settings (BaseSettings) — the ONLY BaseSettings class
    ├── Grouped access via @property (api, email, social, resend)
    └── All fields flat — pydantic-settings reads them directly from .env

Why flat:
  Nested BaseSettings inside BaseSettings causes pydantic to expect
  a dict/object from the env var instead of a plain string — which
  is exactly the ValidationError you hit.
  
  Solution: ONE BaseSettings at root. Group access via @property
  so you still get settings.email.email_user style access.
"""

from enum import StrEnum
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


# ── Enums ──────────────────────────────────────────────────────────────────
class EmailProvider(StrEnum):
    RESEND = "resend"
    GMAIL  = "gmail"


# ── Group models (plain BaseModel — NOT BaseSettings) ──────────────────────
# These are just typed containers for grouped access.
# They never read from .env themselves — Settings does that.

class APIConfig(BaseModel):
    openrouter_api_key: str
    google_api_key:     Optional[str]
    google_cred_path:  Optional[str]
    sheet_name:         Optional[str]


class EmailConfig(BaseModel):
    email_host: str
    email_port: int
    email_user: Optional[str]
    email_pass: Optional[str]

    @field_validator("email_user", mode="before")
    @classmethod
    def validate_email_user(cls, v: Optional[str]) -> Optional[str]:
        if v is None or str(v).strip() == "":
            return None
        if "@" not in str(v):
            raise ValueError("EMAIL_USER must be a valid email address")
        return str(v).strip()


class SocialConfig(BaseModel):
    autobound_api_key: Optional[str]
    github_token:      Optional[str]


class ResendConfig(BaseModel):
    resend_api_key: str
    resend_sender:  str


# ── Root settings ──────────────────────────────────────────────────────────
class Settings(BaseSettings):
    """
    Reads ALL env vars flat from .env.
    Grouped access is provided via @property methods below.
    """

    model_config = {
        "env_file":          "/backend/.env",  # absolute path — works inside Docker
        "env_file_encoding": "utf-8",
        "env_ignore_empty":  True,                 # empty string → use default, not crash
        "extra":             "ignore",
        "case_sensitive":    False,
    }

    # ── App ────────────────────────────────────────────────────────────
    environment: str = Field(
        default="production",
        validation_alias="ENVIRONMENT",
    )
    allowed_origins: List[str] = Field(
        default=["https://www.mohammed-karab.rest"],
        validation_alias="ALLOWED_ORIGINS",
    )
    allowed_hosts: List[str] = Field(
        default=["mohammed-karab.rest", "www.mohammed-karab.rest", "localhost"],
        validation_alias="ALLOWED_HOSTS",
    )
    resume_link: str = Field(
        default="",
        validation_alias="RESUME_LINK",
    )

    # ── Email provider ─────────────────────────────────────────────────
    email_provider: EmailProvider = Field(
        default=EmailProvider.RESEND,
        validation_alias="EMAIL_PROVIDER",
    )

    # ── AI ─────────────────────────────────────────────────────────────
    openrouter_api_key: str = Field(
        default="",
        validation_alias="OPENROUTER_API_KEY",
    )
    google_api_key: Optional[str] = Field(
        default=None,
        validation_alias="GOOGLE_API_KEY",
    )
    google_cred_path: Optional[str] = Field(
        default=None,
        validation_alias="GOOGLE_CREDS_PATH",
    )
    sheet_name: Optional[str] = Field(
        default=None,
        validation_alias="SHEET_NAME",
    )

    # ── Email (shared) ─────────────────────────────────────────────────
    email_host: str = Field(
        default="smtp.gmail.com",
        validation_alias="EMAIL_HOST",
    )
    email_port: int = Field(
        default=587,
        validation_alias="EMAIL_PORT",
    )
    email_user: Optional[str] = Field(
        default=None,
        validation_alias="EMAIL_USER",
    )
    email_pass: Optional[str] = Field(
        default=None,
        validation_alias="EMAIL_PASS",
    )

    # ── Social ─────────────────────────────────────────────────────────
    autobound_api_key: Optional[str] = Field(
        default=None,
        validation_alias="AUTOBOUND_API_KEY",
    )
    github_token: Optional[str] = Field(
        default=None,
        validation_alias="GITHUB_TOKEN",
    )

    # ── Resend ─────────────────────────────────────────────────────────
    resend_api_key: str = Field(
        default="",
        validation_alias="RESEND_API_KEY",
    )
    resend_sender: str = Field(
        default="",
        validation_alias="RESEND_SENDER",
    )

    # ── Admin ──────────────────────────────────────────────────────────
    admin_username: str = Field(
        default="admin",
        validation_alias="ADMIN_USERNAME",
    )
    admin_password_hash: str = Field(
        default="",
        validation_alias="ADMIN_PASSWORD_HASH",
    )
    jwt_secret: str = Field(
        default="change-this-in-production",
        validation_alias="JWT_SECRET",
    )
    # ── Email models ───────────────────────────────────────────────────────────
    model_e1: str = Field(default="", validation_alias="MODEL_E1")
    model_e2: str = Field(default="", validation_alias="MODEL_E2")
    model_e3: str = Field(default="", validation_alias="MODEL_E3")

    # ── Chatbot models ─────────────────────────────────────────────────────────
    model_c1: str = Field(default="", validation_alias="MODEL_C1")
    model_c2: str = Field(default="", validation_alias="MODEL_C2")
    model_c3: str = Field(default="", validation_alias="MODEL_C3")
    # ── Grouped access via properties ──────────────────────────────────

    @property
    def api(self) -> APIConfig:
        return APIConfig(
            openrouter_api_key=self.openrouter_api_key,
            google_api_key=self.google_api_key,
            google_cred_path=self.google_cred_path,
            sheet_name=self.sheet_name,
        )

    @property
    def email(self) -> EmailConfig:
        return EmailConfig(
            email_host=self.email_host,
            email_port=self.email_port,
            email_user=self.email_user,
            email_pass=self.email_pass,
        )

    @property
    def social(self) -> SocialConfig:
        return SocialConfig(
            autobound_api_key=self.autobound_api_key,
            github_token=self.github_token,
        )

    @property
    def resend(self) -> ResendConfig:
        return ResendConfig(
            resend_api_key=self.resend_api_key,
            resend_sender=self.resend_sender,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()