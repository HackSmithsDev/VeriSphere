# ==============================================================================
# Stage 1: Build Dependencies
# ==============================================================================
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build tools for native C-extensions (asyncpg, bcrypt, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Compile wheels into an isolated user directory
RUN pip install --no-cache-dir --user -r requirements.txt

# ==============================================================================
# Stage 2: Minimal Runtime Image
# ==============================================================================
FROM python:3.13-slim AS runner

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create secure non-root system user and configure persistence mount points
RUN groupadd -g 1001 verisphere && \
    useradd -u 1001 -g verisphere -s /bin/bash -m verisphere && \
    mkdir -p /app/data /app/uploads && \
    chown -R verisphere:verisphere /app

# Copy compiled Python packages from builder
COPY --from=builder /root/.local /home/verisphere/.local
ENV PATH=/home/verisphere/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source code, configurations, and migration files
COPY --chown=verisphere:verisphere alembic.ini .
COPY --chown=verisphere:verisphere alembic ./alembic
COPY --chown=verisphere:verisphere app ./app
COPY --chown=verisphere:verisphere main.py .

USER verisphere

EXPOSE 8088

# Health check to ensure FastAPI is actively serving endpoints
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8088/docs || exit 1

# Apply schema migrations before starting the API.
CMD ["sh", "-c", "python -m alembic upgrade head && python main.py"]