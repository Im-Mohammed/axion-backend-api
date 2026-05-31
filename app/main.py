"""
main.py
App factory only. No business logic lives here.

Responsibilities:
  - Create the FastAPI instance
  - Register middleware (CORS, TrustedHost, security headers, rate limiting)
  - Register routers (chatbot, admin, logs)
  - /health endpoint
  - Lifespan (startup / shutdown hooks)

Business logic lives in:
  app/services/email.py      → AI generation + email delivery
  app/services/outreach.py   → GitHub follow + LinkedIn connect
  app/services/portfolio.py  → Portfolio data + prompt builders
  app/services/sheets.py     → Google Sheets backup
  app/settings/config.py     → All environment variables
  app/utils/excel_manager.py → Primary Excel visitor log
  app/utils/rate_limiter.py  → In-memory sliding window rate limiter
  app/router/log_router.py   → Visitor logging routes
  app/router/admin_router.py → Admin panel routes
  app/chatbot/router.py      → Axion chatbot route
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.services.sheets import init_sheets
from app.settings.config import get_settings
from app.utils.rate_limiter import RateLimiter

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)

# Suppress noisy third-party loggers
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("portfolio")

# ── Singletons ─────────────────────────────────────────────────────────────
settings = get_settings()
limiter  = RateLimiter(max_requests=10, window_seconds=60)


# ── Helpers ────────────────────────────────────────────────────────────────
def get_client_ip(request: Request) -> str:
    """
    Extract real client IP.
    Defined here because it's used by the rate_limit middleware
    which runs at app level — before any router.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Portfolio API starting up.")
    init_sheets()
    yield
    logger.info("Portfolio API shutting down.")


# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Mohammed Karab Portfolio API",
    docs_url="/docs"  if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)
# ── Middleware ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]    = "nosniff"
    response.headers["X-Frame-Options"]           = "DENY"
    response.headers["X-XSS-Protection"]          = "1; mode=block"
    response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    ip = get_client_ip(request)
    if not limiter.is_allowed(ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
        )
    return await call_next(request)


# ── Routers ────────────────────────────────────────────────────────────────
from app.chatbot.router import router as chatbot_router
from app.router.admin_router import router as admin_router
from app.router.log_router import router as log_router

app.include_router(chatbot_router)
app.include_router(admin_router)
app.include_router(log_router)


# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}