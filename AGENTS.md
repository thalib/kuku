# AGENTS.md

`kuku` is a Pure Python Desktop-Web Hybrid Business Application.

## Tech Stack

- FastAPI, SQLite, Jinja2, HTMX, Bootstrap 5.3, OpenAI API, pywebview
- Always use `uv` to run the Python app.

## Constraints

- No Docker, Redis, PostgreSQL, Kubernetes, or microservices.
- Single executable distribution.
- Runs completely offline except AI features.
- Use 100% Bootstrap CSS classes for all styling. Custom CSS is allowed only when unavoidable or strictly mandatory.

## Priority & Source of Truth

1. User instructions
2. `SPEC.md` — architecture, UI/UX, components, routing, services, templates; follow and update when behavior changes.
3. `AGENTS.md`
4. Official documentation

- Use Context7 MCP server to fetch the latest documentation.
- `prd/`: ignore unless explicitly provided; use only the provided file, never cross-reference.

## Best Practices

- Follow existing patterns; keep changes minimal, modular, reusable, and production-safe.
- Unless instructed, DO NOT maintain backward compatibility.
- Read `SPEC.md` and relevant source files before coding; identify reusable code and missing requirements first.
- Never guess, invent patterns, refactor unrelated code, or cache backend data between sessions.
- If blocked or uncertain, state: `INSUFFICIENT INFORMATION`.
- Use the Playwright MCP server to test the implementation.
- `README.md` is the very quick minimal quick start file to getting the app up and running.

## Workflow

- Spec-driven development: read existing spec and code → plan → update spec → implement.
- Every code change must be reflected in `SPEC.md`.
- TDD: write a failing test → implement → make it pass before considering work complete.
- Ensure 100% tests pass after every implementation.
- In `SPEC.md`, use h2 (##) for source-level areas, max h3 (###) heading depth.
