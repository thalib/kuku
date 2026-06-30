# --- Stage 1: Build dependencies ---
FROM ghcr.io/astral-sh/uv:1.5.0-python3.11-alpine AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# --- Stage 2: Minimal Runtime ---
FROM python:3.11-alpine AS runner
WORKDIR /app

# FIX: Create appuser AND the data directory, then grant permissions
RUN adduser -D appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

COPY --from=builder /app/.venv /app/.venv
COPY --chown=appuser:appuser ./app ./app

ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_ROOT_PATH="" \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
USER appuser

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 ${APP_ROOT_PATH:+--root-path $APP_ROOT_PATH}"]
