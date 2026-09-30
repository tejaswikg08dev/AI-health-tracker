# ============================================================================
# Health Tracker Backend — Multi-Stage Dockerfile
# ============================================================================
# WHAT IS MULTI-STAGE BUILD:
#   Stage 1 (builder): Install all dependencies — this layer is big (~500MB)
#   Stage 2 (development): Used for local dev — has dev tools + hot reload
#   Stage 3 (production): Copy only what's needed — small, secure final image
#
# WHY:
#   - Production image is ~150MB instead of ~500MB
#   - No dev tools (pytest, ruff) in production = smaller attack surface
#   - Faster deploys (smaller image to push/pull)
#
# This is how every company builds Docker images.
# ============================================================================

# ── Stage 1: Builder ──
# Install Python dependencies into a separate prefix
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system dependencies needed for building Python packages
# gcc, libpq-dev needed for psycopg2 (PostgreSQL driver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer
# If requirements don't change, this layer is reused (fast rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Development ──
# Used when docker-compose.dev.yml sets target: development
FROM python:3.11-slim AS development

WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy dev requirements and install them too
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY . .

# Development server with hot reload
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# ── Stage 3: Production ──
# Minimal image — only what's needed to run the app
FROM python:3.11-slim AS production

WORKDIR /app

# Install only runtime system dependencies (no gcc, no dev headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# SECURITY: Create non-root user
# Production apps should NEVER run as root
# If an attacker exploits the app, they get limited permissions
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code only (no tests, no dev files)
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Switch to non-root user
USER appuser

EXPOSE 8000

# Production server: gunicorn with uvicorn workers
# gunicorn manages worker processes (restart on crash, graceful shutdown)
# uvicorn workers handle async requests
CMD ["gunicorn", "app.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
