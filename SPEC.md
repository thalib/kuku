# SPEC.md

## Overview

`kuku` is "Kuku" — a desktop-web hybrid business application built with Python. It runs as a native desktop window (pywebview) or a local web server, using FastAPI on the backend with HTMX for dynamic UI interactions.

## Architecture

### Stack

| Layer       | Technology          |
|-------------|---------------------|
| Backend     | FastAPI, Python     |
| Database    | SQLite              |
| Frontend    | Jinja2, HTMX, Bootstrap 5.3 |
| Desktop     | pywebview           |
| AI          | OpenAI API          |
| Packaging   | Single executable (PyInstaller) |

### Runtime Modes

- **Desktop** — pywebview window wrapping FastAPI (default)
- **Browser** — FastAPI dev server at `http://localhost:8000`
- **Network** — `uvicorn main:app --host 0.0.0.0 --port 8000` (LAN access)

## Directory Structure

```
kuku/
├── main.py              # Entry point
├── pyproject.toml       # Project config & dependencies
├── AGENTS.md
├── SPEC.md
├── app/
│   ├── __init__.py
│   ├── config.py        # App settings & constants
│   ├── database.py      # SQLite connection & setup
│   ├── models/          # Pydantic models
│   ├── routers/         # FastAPI route modules
│   ├── services/        # Business logic
│   ├── static/          # CSS, JS, images
│   └── templates/       # Jinja2 HTML templates
│       ├── layouts/     # Base layouts
│       ├── partials/    # HTMX partials
│       └── pages/       # Full page templates
└── tests/
```

## Routes

| Method | Path | Description   |
|--------|------|---------------|
| GET    | /    | Dashboard     |

[TODO] Define routes as features are implemented.

## Database Schema

[TODO] Define tables as features are implemented.

## UI/UX

- Bootstrap 5.3 responsive layout
- HTMX for dynamic partial updates (no full page reloads)
- Sidebar navigation (offcanvas): Dashboard, Transactions, GST, Reports
- Theme support: dark (default via Bootstrap data-bs-theme)

## Services

### AI Service (OpenAI)

[TODO] Define integration points for OpenAI API calls.

## Testing

- Framework: pytest
- Run: `uv run pytest`
- Coverage: report after each run
- Integration tests use Playwright for UI verification
- TDD: write failing test → implement → make it pass

## Configuration

| Key              | Default              | Description          |
|------------------|----------------------|----------------------|
| `APP_HOST`       | `127.0.0.1`          | Server bind host     |
| `APP_PORT`       | `8000`               | Server bind port     |
| `OPENAI_API_KEY` | (env)                | OpenAI API key       |
| `DB_PATH`        | `sqlite.db`          | SQLite database file |
