# ==============================================================================
# HazardIQ Backend - Production Dockerfile for AWS App Runner
# ==============================================================================
# Multi-stage lightweight Python container with security hardening (non-root user).
# ==============================================================================

FROM python:3.12-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY . .

# Create non-root system user for security compliance
RUN useradd -m -u 10001 hazardiq && \
    chown -R hazardiq:hazardiq /app

USER hazardiq

# Expose standard App Runner / container port
EXPOSE 8000

# App Runner Health Check verification
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Production server entrypoint (dynamically binds to cloud-assigned $PORT)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
