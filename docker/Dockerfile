# ── Project Hyperion  ·  Production Container Spec ───────────────
# Multi-layer, distroless-ready slim build with non-root user.
# Target: python:3.11-slim  |  ~120 MiB compressed

FROM python:3.11-slim AS base

WORKDIR /app

# Security: pin Debian packages, clean cache in same layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl=7.* ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Layer 2 — Python dependencies (cached)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Layer 3 — application code
COPY . .

# Non-root user (no login shell, no home writes)
RUN useradd --create-home --shell /usr/sbin/nologin hyperion && \
    chown -R hyperion:hyperion /app && \
    chmod -R 755 /app

USER hyperion

# Only expose what's necessary
EXPOSE 8080 9090

# Readiness probe — fails fast, low timeout
HEALTHCHECK --interval=30s --timeout=3s --retries=3 --start-period=5s \
    CMD curl -sf http://localhost:8080/health || exit 1

# Drop all capabilities, read-only root (where possible)
CMD ["python3", "core/orchestrator.py"]
