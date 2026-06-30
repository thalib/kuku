# --- Stage 1: Build dependencies ---
FROM ghcr.io/astral-sh/uv:python3.11-alpine AS builder

WORKDIR /app

# Enable bytecode compilation for faster startup and smaller footprint
ENV UV_COMPILE_BYTECODE=1

# Install dependencies into a localized virtual environment (.venv)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# --- Stage 2: Minimal Runtime ---
FROM python:3.11-alpine AS runner

WORKDIR /app

# Create a non-privileged user for security
RUN adduser -D appuser && chown -R appuser:appuser /app

# Copy the pre-compiled virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY --chown=appuser:appuser . .

# Set environment variables
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_ROOT_PATH="" \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

USER appuser

# Run uvicorn directly from the virtual environment path (drops uv tool overhead)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 ${APP_ROOT_PATH:+--root-path $APP_ROOT_PATH}"]
