import io

import jinja2
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from xhtml2pdf import pisa
import os

from app.config import APP_NAME, NAV_GROUPS, COMPANY_NAME, APP_ROOT_PATH
from app.database import get_db
from app.services import reports as report_svc
from app.utils.nav import mark_active_nav
from app.utils.templates import templates

router = APIRouter()

_export_template_dir = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "templates", "exports"
)
_export_jinja = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_export_template_dir),
    autoescape=True,
)


def _fy_label(fy_start: int) -> str:
    return f"FY {fy_start}-{fy_start + 1}"


def _ctx(page_url: str, page_name: str) -> dict:
    return {
        "app_name": APP_NAME,
        "page_title": f"{page_name} - {APP_NAME}",
        "nav_groups": mark_active_nav(NAV_GROUPS, page_url),
    }


def _render_pdf(pdf_template: str, html_content: str, filename: str) -> StreamingResponse:
    pdf_bytes = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html_content), dest=pdf_bytes)
    pdf_bytes.seek(0)
    return StreamingResponse(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/fy-years")
async def report_fy_years() -> JSONResponse:
    db = await get_db()
    years = await report_svc.get_report_fy_years(db)
    return JSONResponse({"fy_years": years})


@router.get("/reports", response_class=HTMLResponse)
async def reports_index(request: Request):
    from fastapi.responses import RedirectResponse
    root = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root}/reports/profit-loss", status_code=302)


@router.get("/reports/balance-sheet", response_class=HTMLResponse)
async def balance_sheet_page(request: Request):
    return templates.TemplateResponse(request, "pages/reports/balance_sheet.html", _ctx("/reports/balance-sheet", "Balance Sheet"))


@router.get("/reports/balance-sheet/content", response_class=HTMLResponse)
async def balance_sheet_content(request: Request, fy: int):
    db = await get_db()
    data = await report_svc.get_balance_sheet(db, fy)
    root = request.scope.get("root_path", "")
    return templates.TemplateResponse(request, "partials/reports/balance_sheet_content.html", {
        "data": data,
        "selected_fy": fy,
        "fy_label": _fy_label(fy),
        "report_name": "Balance Sheet",
        "pdf_url": f"{root}/reports/balance-sheet/pdf?fy={fy}",
        "company_name": COMPANY_NAME,
    })


@router.get("/reports/balance-sheet/pdf", response_class=StreamingResponse)
async def balance_sheet_pdf(request: Request, fy: int):
    db = await get_db()
    data = await report_svc.get_balance_sheet(db, fy)
    tmpl = _export_jinja.get_template("reports/balance_sheet/pdf.html")
    html = tmpl.render(data=data, company_name=COMPANY_NAME, fy_label=_fy_label(fy))
    return _render_pdf("reports/balance_sheet/pdf.html", html, f"balance_sheet_{fy}_{fy+1}.pdf")


@router.get("/reports/profit-loss", response_class=HTMLResponse)
async def profit_loss_page(request: Request):
    return templates.TemplateResponse(request, "pages/reports/profit_loss.html", _ctx("/reports/profit-loss", "Profit and Loss"))


@router.get("/reports/profit-loss/content", response_class=HTMLResponse)
async def profit_loss_content(request: Request, fy: int):
    db = await get_db()
    data = await report_svc.get_profit_loss(db, fy)
    root = request.scope.get("root_path", "")
    return templates.TemplateResponse(request, "partials/reports/profit_loss_content.html", {
        "data": data,
        "selected_fy": fy,
        "fy_label": _fy_label(fy),
        "report_name": "Profit and Loss",
        "pdf_url": f"{root}/reports/profit-loss/pdf?fy={fy}",
        "company_name": COMPANY_NAME,
    })


@router.get("/reports/profit-loss/pdf", response_class=StreamingResponse)
async def profit_loss_pdf(request: Request, fy: int):
    db = await get_db()
    data = await report_svc.get_profit_loss(db, fy)
    tmpl = _export_jinja.get_template("reports/profit_loss/pdf.html")
    html = tmpl.render(data=data, company_name=COMPANY_NAME, fy_label=_fy_label(fy))
    return _render_pdf("reports/profit_loss/pdf.html", html, f"profit_loss_{fy}_{fy+1}.pdf")


@router.get("/reports/cash-flow", response_class=HTMLResponse)
async def cash_flow_page(request: Request):
    return templates.TemplateResponse(request, "pages/reports/cash_flow.html", _ctx("/reports/cash-flow", "Cash Flow"))


@router.get("/reports/cash-flow/content", response_class=HTMLResponse)
async def cash_flow_content(request: Request, fy: int):
    db = await get_db()
    data = await report_svc.get_cash_flow(db, fy)
    root = request.scope.get("root_path", "")
    return templates.TemplateResponse(request, "partials/reports/cash_flow_content.html", {
        "data": data,
        "selected_fy": fy,
        "fy_label": _fy_label(fy),
        "report_name": "Cash Flow Statement",
        "pdf_url": f"{root}/reports/cash-flow/pdf?fy={fy}",
        "company_name": COMPANY_NAME,
    })


@router.get("/reports/cash-flow/pdf", response_class=StreamingResponse)
async def cash_flow_pdf(request: Request, fy: int):
    db = await get_db()
    data = await report_svc.get_cash_flow(db, fy)
    tmpl = _export_jinja.get_template("reports/cash_flow/pdf.html")
    html = tmpl.render(data=data, company_name=COMPANY_NAME, fy_label=_fy_label(fy))
    return _render_pdf("reports/cash_flow/pdf.html", html, f"cash_flow_{fy}_{fy+1}.pdf")
