from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from app.config import APP_NAME, NAV_GROUPS
from app.database import init_db, close_db
from app.routers import bank_accounts, bank_transactions, categories, rules
from app.utils.nav import mark_active_nav
import os


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Kuku", lifespan=lifespan)

_static_dir = os.path.join(os.path.dirname(__file__), "static")
_template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_template_dir)

app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.include_router(bank_accounts.router, prefix="/banks", tags=["Bank Accounts"])
app.include_router(bank_transactions.router, prefix="/banks", tags=["Transactions"])
app.include_router(categories.router, prefix="/banks", tags=["Categories"])
app.include_router(rules.router, prefix="/banks", tags=["Rules"])


def _render_page(request: Request, page_url: str, page_name: str):
    return templates.TemplateResponse(
        request,
        "pages/coming_soon.html",
        {
            "app_name": APP_NAME,
            "page_title": f"{page_name} - Kuku",
            "page_name": page_name,
            "nav_groups": mark_active_nav(NAV_GROUPS, page_url),
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
            "nav_groups": mark_active_nav(NAV_GROUPS, "/"),
        },
    )


@app.get("/reports", response_class=HTMLResponse)
async def reports(request: Request):
    return _render_page(request, "/reports", "Reports")



