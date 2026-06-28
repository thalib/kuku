# AGENTS.md

`kuku` ("Kuku") — Pure Python Desktop-Web Hybrid Business Application.

## Tech Stack

- FastAPI, SQLite, Jinja2, HTMX, Bootstrap 5.3, OpenAI API, pywebview
- Python ≥ 3.11
- Always use `uv` to run the Python app.
- Package manager: `uv` (no pip, no conda)

## Constraints

- No Docker, Redis, PostgreSQL, Kubernetes, or microservices.
- Single executable distribution.
- Runs completely offline except AI features.
- Use 100% Bootstrap CSS classes for all styling. Custom CSS is allowed only when unavoidable or strictly mandatory.
- No third-party JS frameworks (React, Vue, Alpine, etc.). HTMX only for dynamic UI.
- No client-side state management libraries. Keep state server-side.

## Priority & Source of Truth

1. **User instructions** — highest authority
2. **`SPEC.md`** — architecture, UI/UX, components, routing, services, templates; follow and update when behavior changes
3. **`AGENTS.md`** — this file
4. **Official documentation** — use Context7 MCP server for latest docs
5. **Existing codebase** — patterns already in the project

- `prd/`: ignore unless explicitly provided; use only the provided file, never cross-reference

## Code Architecture Principles

### Modularity

- One responsibility per file. If a file does more than one thing, split it.
- Templates: use `{% include %}` and `{% extends %}` aggressively. Never duplicate markup across pages.
- Python: extract shared logic into `app/services/`, `app/models/`, or `app/utils/`.
- Routes with common patterns (coming soon, CRUD scaffolding) must use helper functions — never duplicate route boilerplate.
- Config values live in `app/config.py`, never hardcoded in templates or views.

### DRY — Do Not Repeat Yourself

- If a pattern appears more than once, extract it into a reusable component, helper, or template partial.
- Jinja2 templates MUST use `{% macro %}` for repeated UI elements (table rows, form fields, cards).
- Python: extract repeated logic into functions or classes before it appears a third time (the "rule of three").
- Test helpers and fixtures belong in `tests/conftest.py`, not duplicated across test files.

### Reusability

- Build small, composable units: template partials, service functions, Pydantic models.
- Components must be parameterized — no hardcoded strings, URLs, or IDs inside reusable pieces.
- Services are pure where possible: same input → same output, no hidden globals.
- Never mix concerns: data access in services, presentation in templates, routing in views.

## UI/UX Standards

### Layout

- Fixed top navbar (`sticky-top`) + sidebar + scrollable content area.
- Sidebar is a permanent panel (248px), toggleable collapse/expand via button.
- Content area has `bg-light` background. Navbar and sidebar use `bg-dark`.
- Use `vh-100` and flexbox for full-height layouts. Prevent double scrollbars.

### Visual Density

- Compact, lean, clean. Follow Bootstrap's default spacing — do not add custom padding/margins without reason.
- Tables: `table-sm`, `table-hover`, `align-middle`.
- Cards: `border-0 shadow-sm` for elevated surfaces.
- Typography: use Bootstrap's type scale (`h1`–`h6`, `small`, `text-muted`). No custom font sizes unless unavoidable.

### Performance

- Minimize DOM depth. Avoid deeply nested `<div>` wrappers.
- Use HTMX for partial updates — never full page reloads for data changes.
- Lazy-load non-critical scripts. Bootstrap JS at the end of `<body>`.
- No unnecessary re-renders. Jinja2 templates should not loop over data that hasn't changed.

### Icons

- Bootstrap Icons only (`bi-*`). No Font Awesome, no inline SVG unless unavoidable.
- Icons must have `flex-shrink-0` inside flex containers to prevent distortion.

## Coding Standards

### Python

- Type hints on all public function signatures.
- Use `pathlib.Path` for file paths, never string concatenation.
- Use `async/await` for all I/O operations.
- Database queries go through `app/database.py` — no raw SQL in views.
- Pydantic for request/response schemas and settings validation.
- Error handling: return proper HTTP status codes. Never let exceptions leak as 500s without logging.
- No `print()` statements in production code. Use `logging` module.

### Templates (Jinja2)

- Prefer `block` inheritance over duplication.
- Use dictionary bracket access (`item["key"]`) not dot notation for dicts — avoids Jinja2/Python name conflicts.
- Template variables are **always** validated at the route layer. Never assume a key exists.
- Navigation active state is computed server-side (`_mark_active`) — never CSS-based or JS-based hacks.

### CSS

- Bootstrap utility classes first. Custom CSS only as last resort.
- Custom CSS goes in `app/static/css/custom.css`, never inline `<style>` in templates.
- CSS custom properties (`--var`) for repeated values (colors, widths).
- No `!important` unless overriding Bootstrap defaults that cannot be changed otherwise.

## Workflow

### Spec-Driven Development

1. Read existing `SPEC.md` and relevant source files
2. Identify what exists, what's missing, what's reusable
3. Plan the change
4. Update `SPEC.md` with the new behavior
5. Write a failing test
6. Implement the minimum code to pass
7. Verify 100% tests pass
8. Confirm visual output with Playwright MCP

### TDD Enforcement

- **Every** new feature starts with a failing test. No exceptions.
- Test file per feature group: `tests/test_<feature>.py`.
- Use parametrized tests (`@pytest.mark.parametrize`) to avoid duplicating test logic.
- If a test is complex, split it. One assertion cluster per test method.
- `uv run pytest` must pass after **every** implementation turn.

### Before Any Code Change

- Read `SPEC.md` — understand the current state
- Read relevant source files — understand the existing patterns
- Search for existing implementations of similar patterns — reuse before creating
- If a pattern already exists, use it. Do not invent a new one.

## Anti-Hallucination Rules

These rules prevent the AI from making assumptions, inventing features, or deviating from the project:

### What NOT to Do

- **NEVER commit** unless the user explicitly asks you to commit.
- **Do not invent features** not described in `SPEC.md` or user instructions.
- **Do not assume** dependencies exist. Check `pyproject.toml` first.
- **Do not assume** a file exists. Check with `Read` or `Glob` first.
- **Do not guess** API signatures, Jinja2 syntax, or Bootstrap class names. Verify with Context7 or the docs.
- **Do not cache** backend data between sessions or assume state persists.
- **Do not refactor** unrelated code. Scope changes tightly.
- **Do not maintain** backward compatibility unless explicitly instructed.
- **Do not create** documentation files (*.md), READMEs, or docstrings unless explicitly requested.
- **Do not add** comments explaining code unless explicitly asked.
- **Do not guess** project conventions from other projects. Follow the patterns in this codebase.

### What TO Do

- If blocked or uncertain, state: `INSUFFICIENT INFORMATION` and ask the user.
- If a dependency is needed but not in `pyproject.toml`, add it there first, then install.
- If a pattern is unclear, read the most similar existing implementation and follow it exactly.
- If `SPEC.md` is incomplete, flag the gap and ask for clarification before implementing.
- Always validate your work: run tests, check visual output, verify against spec.

### Verification Checklist

After every implementation turn, confirm:

- [ ] All tests pass (`uv run pytest`)
- [ ] No new warnings or errors in the server log
- [ ] Visual output matches the spec (use Playwright MCP)
- [ ] `SPEC.md` is updated to reflect the change
- [ ] No unused imports, dead code, or orphan files
- [ ] Code follows existing patterns in the codebase

### SPEC.md Formatting

- Use `##` for source-level areas, max heading depth `###`.
- Every behavior change must be reflected in `SPEC.md`.

### README.md

- `README.md` is a very quick, minimal quick-start file for getting the app up and running. Nothing more.

## File Structure

```
kuku/
├── main.py                # Server entry point
├── pyproject.toml         # Dependencies and project config
├── SPEC.md                # Source of truth for architecture
├── AGENTS.md              # This file
├── README.md              # Quick start
├── app/
│   ├── __init__.py
│   ├── config.py          # All config constants (nav, urls, settings)
│   ├── database.py        # DB connection and initialization
│   ├── main.py            # FastAPI app, routes
│   ├── models/            # Pydantic schemas, data models
│   ├── routers/           # Route modules (when split from main.py)
│   ├── services/          # Business logic (reusable, pure where possible)
│   ├── static/
│   │   ├── css/           # Custom CSS (only when unavoidable)
│   │   ── js/            # Custom JS (only when unavoidable)
│   └── templates/
│       ├── layouts/       # Base templates ({% extends %})
│       ├── pages/         # Page templates
│       └── partials/      # Reusable fragments ({% include %})
└── tests/
    ├── __init__.py
    ├── conftest.py        # Shared fixtures
    └── test_*.py          # Test files per feature
```

## Naming Conventions

- Python files: `snake_case.py`
- Template files: `snake_case.html`
- CSS custom properties: `--kuku-*`
- Jinja2 blocks: `block content`, `block extra_head`, `block extra_scripts`
- HTMX IDs: `#hx-*` prefix for HTMX-triggered elements
- Test functions: `test_<what_is_being_tested>`
- Route URLs: kebab-case (`/banks/manage`, `/purchase-orders`)

## Security

- Never log or expose secrets, API keys, or credentials.
- Use Jinja2's auto-escaping (enabled by default). Never use `|safe` unless input is sanitized.
- HTMX requests must be validated server-side. Never trust client-side data.
- All user input must be validated with Pydantic before processing.
