# ── Base stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /backend

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser

# Create logs directory and give ownership to appuser BEFORE switching user
RUN mkdir -p /backend/logs && chown -R appuser:appuser /backend

# Copy application code
COPY app/ ./app/

# Switch to non-root user
USER appuser

EXPOSE 8000

# ── Development ─────────────────────────────────────────────────────────────
FROM base AS development
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--reload-dir", "/backend/app"]

# ── Production ──────────────────────────────────────────────────────────────
FROM base AS production
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2"]