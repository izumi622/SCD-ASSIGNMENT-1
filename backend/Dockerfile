# ========================================================
# Stage 1: Build & Dependency Wheel Stage
# ========================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install compilation tools if any C extensions are needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Cache-friendly dependency installation
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ========================================================
# Stage 2: Final Minimal Runtime Stage (Non-Root)
# ========================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Install minimal runtime shared libraries (curl for healthcheck, libpq5 for postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Security: Create non-root system user and group
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Copy application source code
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup alembic/ ./alembic/
COPY --chown=appuser:appgroup alembic.ini .

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Healthcheck probe pointing to /health (does not touch database)
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Exec-form CMD
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
