"""
outreach.py
GitHub follow and LinkedIn connection request.
Both are fire-and-forget — failures are logged, not raised.
"""

import logging
import requests
from app.settings.config import get_settings

logger   = logging.getLogger("portfolio.outreach")
settings = get_settings()


def follow_on_github(username: str):
    if not username or not settings.social.github_token:
        return
    try:
        r = requests.put(
            f"https://api.github.com/user/following/{username}",
            headers={
                "Authorization": f"token {settings.social.github_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=5,
        )
        if r.status_code in (204, 304):
            logger.info(f"GitHub: followed {username}")
        else:
            logger.warning(f"GitHub follow failed ({r.status_code})")
    except Exception as e:
        logger.error(f"GitHub follow error: {e}")


def connect_on_linkedin(name: str, email: str):
    if not name or not settings.social.autobound_api_key:
        return
    try:
        requests.post(
            "https://api.autobound.ai/api/external/generate-content/v1",
            headers={
                "X-API-KEY": settings.social.autobound_api_key,
                "Content-Type": "application/json",
            },
            json={
                "contactEmail": email or f"{name.lower().replace(' ', '')}@example.com",
                "userEmail":    settings.email.email_user,
                "contentType":  "connectionRequest",
            },
            timeout=5,
        )
        logger.info(f"LinkedIn outreach triggered for {name}")
    except Exception as e:
        logger.error(f"LinkedIn outreach failed: {e}")