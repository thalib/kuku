FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
ENV APP_ROOT_PATH=

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 ${APP_ROOT_PATH:+--root-path $APP_ROOT_PATH}"]
