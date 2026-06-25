from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.config import APP_NAME, NAV_GROUPS, QUICK_LINKS
import os

app = FastAPI(title="Kuku")

_static_dir = os.path.join(os.path.dirname(__file__), "static")
_template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_template_dir)


def _mark_active(groups, active_name):
    groups = [dict(g) for g in groups]
    for g in groups:
        original_links = list(g.get("links", []))
        g["links"] = [{**lk, "active": lk["name"] == active_name} for lk in original_links]
    return groups


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "app_name": APP_NAME,
            "page_title": "Dashboard - Kuku",
            "nav_groups": _mark_active(NAV_GROUPS, "Dashboard"),
            "quick_links": QUICK_LINKS,
            "current_page": "dashboard",
        },
    )
