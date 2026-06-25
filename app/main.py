from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.config import APP_NAME, NAV_GROUPS
import os

app = FastAPI(title="Kuku")

_static_dir = os.path.join(os.path.dirname(__file__), "static")
_template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_template_dir)


def _mark_active(groups, page_url):
    groups = [dict(g) for g in groups]
    for g in groups:
        original_links = list(g.get("links", []))
        g["links"] = [{**lk, "active": lk["url"] == page_url} for lk in original_links]
    return groups


def _render_page(request: Request, page_url: str, page_name: str):
    return templates.TemplateResponse(
        request,
        "pages/coming_soon.html",
        {
            "app_name": APP_NAME,
            "page_title": f"{page_name} - Kuku",
            "page_name": page_name,
            "nav_groups": _mark_active(NAV_GROUPS, page_url),
        },
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "app_name": APP_NAME,
            "page_title": "Dashboard - Kuku",
            "nav_groups": _mark_active(NAV_GROUPS, "/"),
        },
    )


@app.get("/banks/manage", response_class=HTMLResponse)
async def banks_manage(request: Request):
    return _render_page(request, "/banks/manage", "Banks - Manage")


@app.get("/banks/transactions", response_class=HTMLResponse)
async def banks_transactions(request: Request):
    return _render_page(request, "/banks/transactions", "Banks - Transaction")


@app.get("/reports", response_class=HTMLResponse)
async def reports(request: Request):
    return _render_page(request, "/reports", "Reports")


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return _render_page(request, "/settings", "Admin - Settings")
