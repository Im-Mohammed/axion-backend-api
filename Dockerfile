# ── Base stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /backend

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user and logs directory
RUN adduser --disabled-password --gecos "" appuser && \
    mkdir -p /backend/logs

# Copy application code
COPY app/ ./app/

# Give appuser ownership of everything — must be AFTER COPY
RUN chown -R appuser:appuser /backend

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