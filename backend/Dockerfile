# Multi-arch compatible (ARM64 + AMD64) — Python 3.12 slim
FROM python:3.12-slim

# Build args
ARG TARGETPLATFORM
ARG BUILDPLATFORM

LABEL org.opencontainers.image.source="https://github.com/Damianjsp/madrid-rental-finder"
LABEL org.opencontainers.image.description="Madrid Rental Finder — backend API"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

# Copy source
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini
COPY scripts/ ./scripts/

# Non-root user
RUN useradd -m -u 1000 mrf && chown -R mrf:mrf /app
USER mrf

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "mrf.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
