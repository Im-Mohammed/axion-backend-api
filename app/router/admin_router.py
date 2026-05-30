"""
admin_router.py
Secure /admin panel — password-protected, JWT-issued session tokens,
serves the Excel visitor log and stats.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from pathlib import Path
import os
import logging
import bcrypt
import jwt

logger = logging.getLogger("portfolio.admin")
router = APIRouter(prefix="/admin", tags=["admin"])

# ── Config from env ─────────────────────────────────────────────────────────
ADMIN_USERNAME      = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")   # bcrypt hash
JWT_SECRET          = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGORITHM       = "HS256"
JWT_EXPIRE_HOURS    = 8

security = HTTPBearer(auto_error=False)


# ── JWT helpers ─────────────────────────────────────────────────────────────
def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Login endpoint ──────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def admin_login(data: LoginRequest):
    """Validate credentials and return a JWT."""
    if data.username != ADMIN_USERNAME:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not ADMIN_PASSWORD_HASH:
        raise HTTPException(status_code=500, detail="Admin password not configured")

    try:
        valid = bcrypt.checkpw(
            data.password.encode("utf-8"),
            ADMIN_PASSWORD_HASH.encode("utf-8"),
        )
    except Exception as e:
        logger.error(f"bcrypt error: {e}")
        valid = False

    if not valid:
        logger.warning(f"Failed admin login attempt for user '{data.username}'")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(data.username)
    logger.info(f"Admin '{data.username}' logged in.")
    return {"token": token, "expires_in_hours": JWT_EXPIRE_HOURS}


# ── Protected data endpoints ────────────────────────────────────────────────
@router.get("/stats")
def admin_stats(username: str = Depends(verify_token)):
    from backend.app.utils.excel_manager import ExcelManager
    excel = ExcelManager("logs/visitors.xlsx")
    return excel.get_stats()


@router.get("/visitors")
def admin_visitors(
    page: int = 1,
    per_page: int = 50,
    user_type: str = "",
    username: str = Depends(verify_token),
):
    from backend.app.utils.excel_manager import ExcelManager
    excel   = ExcelManager("logs/visitors.xlsx")
    records = excel.get_all_visitors()

    # Optional filter
    if user_type:
        records = [r for r in records if r.get("UserType") == user_type]

    # Sort newest first
    records.sort(key=lambda r: str(r.get("Timestamp", "")), reverse=True)

    total      = len(records)
    start      = (page - 1) * per_page
    paginated  = records[start : start + per_page]

    # Strip long body from listing (send summary only)
    for r in paginated:
        if r.get("Body") and len(r["Body"]) > 120:
            r["Body"] = r["Body"][:120] + "…"

    return {
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
        "data":     paginated,
    }


@router.get("/visitor/{visitor_id}")
def admin_visitor_detail(visitor_id: str, username: str = Depends(verify_token)):
    from backend.app.utils.excel_manager import ExcelManager
    excel   = ExcelManager("logs/visitors.xlsx")
    records = excel.get_all_visitors()
    record  = next((r for r in records if r.get("ID") == visitor_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return record


@router.get("/export")
def admin_export(username: str = Depends(verify_token)):
    """Download the raw Excel file."""
    filepath = "logs/visitors.xlsx"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="No log file found")

    with open(filepath, "rb") as f:
        content = f.read()

    filename = f"visitors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Admin SPA (serves the HTML dashboard shell) ─────────────────────────────
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_ui():
    """
    Serves the admin dashboard SPA.
    The actual HTML file is at admin/index.html next to main.py.
    """
    html_path = Path(__file__).parent.parent / "admin" / "index.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Admin panel not found</h1>", status_code=404)
    return HTMLResponse(html_path.read_text())