from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.config import APP_NAME, NAV_ITEMS
import os

app = FastAPI(title="Kuku")

_static_dir = os.path.join(os.path.dirname(__file__), "static")
_template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_template_dir)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "app_name": APP_NAME,
            "page_title": "Dashboard - Kuku",
            "nav_items": NAV_ITEMS,
        },
    )
