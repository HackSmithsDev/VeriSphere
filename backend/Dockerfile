# ==============================================================================
# Stage 1: Build Dependencies
# ==============================================================================
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build-time dependencies for native C-extensions (asyncpg, bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Compile wheels into an isolated user folder
RUN pip install --no-cache-dir --user -r requirements.txt

# ==============================================================================
# Stage 2: Minimal Runtime Image
# ==============================================================================
FROM python:3.13-slim AS runner

WORKDIR /app

# Install minimal runtime shared libraries (libpq for postgres communication)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root system user for secure container execution
RUN groupadd -g 1001 aera && \
    useradd -u 1001 -g aera -s /bin/bash -m aera

# Copy compiled Python packages from the builder stage
COPY --from=builder /root/.local /home/aera/.local
ENV PATH=/home/aera/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source code and migrations
COPY --chown=aera:aera alembic.ini .
COPY --chown=aera:aera alembic ./alembic
COPY --chown=aera:aera app ./app
COPY --chown=aera:aera main.py .

USER aera

EXPOSE 8088

# Health check to ensure ASGI server is accepting connections
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8088/docs || exit 1

# Launch production server with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8088", "--proxy-headers", "--forwarded-allow-ips=*"]