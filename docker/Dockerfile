# ── Project Hyperion  ·  Production Container Spec ───────────────
# Multi-layer slim build with non-root runtime user.
# Target: python:3.11-slim  |  ~120 MiB compressed

FROM python:3.11-slim AS base

WORKDIR /app

# Layer 1 — system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Layer 2 — Python dependencies (cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Layer 3 — application code
COPY . .

# Non-root runtime user
RUN useradd --create-home --shell /bin/bash hyperion && \
    chown -R hyperion:hyperion /app
USER hyperion

EXPOSE 8080 9090

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -sf http://localhost:8080/health || exit 1

CMD ["python3", "core/orchestrator.py"]
