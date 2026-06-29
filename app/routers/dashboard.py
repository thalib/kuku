from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.config import APP_NAME, NAV_GROUPS
from app.database import get_db
from app.services import dashboard as dash_svc
from app.services.transactions import MONTHS
from app.utils.nav import mark_active_nav
from app.utils.templates import templates

router = APIRouter()


def _fy_label(fy_start: int) -> str:
    return f"FY {fy_start}-{fy_start + 1}"


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "app_name": APP_NAME,
            "page_title": "Dashboard - Kuku",
            "nav_groups": mark_active_nav(NAV_GROUPS, "/"),
        },
    )


@router.get("/content", response_class=HTMLResponse)
async def dashboard_content(
    request: Request,
    fy: int | None = None,
    month: int | None = None,
):
    db = await get_db()
    fy_years = await dash_svc.get_available_fy_years(db)

    if fy is None and fy_years:
        fy = max(fy_years)
    elif fy is None:
        fy = 0

    available_months = []
    if fy:
        available_months = await dash_svc.get_available_months(db, fy)

    if month is not None and month not in available_months:
        month = None

    data = {}
    if fy:
        data = await dash_svc.get_dashboard_data(db, fy, month)

    accounts = data.get("accounts") or await dash_svc.get_accounts_with_balance(db)

    return templates.TemplateResponse(
        request,
        "partials/dashboard_content.html",
        {
            "app_name": APP_NAME,
            "fy_years": fy_years,
            "months": MONTHS,
            "selected_fy": fy,
            "selected_month": month,
            "available_months": available_months,
            "fy_label": _fy_label(fy) if fy else "",
            "data": data,
            "accounts": accounts,
            "has_data": bool(fy),
        },
    )
