import logging
from calendar import month_abbr
from datetime import date

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import APP_NAME, NAV_GROUPS
from app.database import get_db
from app.services import cash_in_hand as cash_svc
from app.services import transactions as tx_svc
from app.models.transactions import CashInHandCreate, CashInHandUpdate
from app.utils.nav import mark_active_nav
from app.utils.templates import templates

router = APIRouter()

logger = logging.getLogger(__name__)

MONTHS = [
    (1, "JAN"), (2, "FEB"), (3, "MAR"), (4, "APR"),
    (5, "MAY"), (6, "JUN"), (7, "JUL"), (8, "AUG"),
    (9, "SEP"), (10, "OCT"), (11, "NOV"), (12, "DEC"),
]

FY_MONTH_ORDER = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]

FY_RANGE_BEFORE = 2
FY_RANGE_AFTER = 1


def _current_fy() -> int:
    now = date.today()
    return now.year if now.month >= 4 else now.year - 1


def _fy_range() -> list[int]:
    fy = _current_fy()
    return list(range(fy - FY_RANGE_BEFORE, fy + FY_RANGE_AFTER + 1))


def _base_ctx(request: Request, page_url: str, page_name: str):
    return {
        "app_name": APP_NAME,
        "page_title": f"{page_name} - Kuku",
        "nav_groups": mark_active_nav(NAV_GROUPS, page_url),
    }


@router.get("/cash-in-hand", response_class=HTMLResponse)
async def cash_in_hand_page(request: Request):
    ctx = _base_ctx(request, "/banks/cash-in-hand", "Cash in Hand")
    return templates.TemplateResponse(request, "pages/cash_in_hand.html", ctx)


@router.get("/cash-in-hand/filters", response_class=HTMLResponse)
async def cash_in_hand_filters(request: Request, selected_fy: int | None = None, selected_month: int | None = None):
    db = await get_db()
    fy_years = _fy_range()
    cur_fy = _current_fy()
    fy = selected_fy if selected_fy and selected_fy in fy_years else cur_fy

    try:
        data_months = set(await cash_svc.get_available_months(db, fy))
    except Exception:
        data_months = set()

    months = []
    for m in FY_MONTH_ORDER:
        cal_year = tx_svc.fy_to_calendar(fy, m)
        label = f"{MONTHS[m - 1][1]} {cal_year}"
        months.append((m, label, m in data_months))

    now = date.today()
    if selected_month and 1 <= selected_month <= 12:
        sel_month = selected_month
    else:
        sel_month = now.month

    ctx = {
        "fy_years": fy_years, "months": months,
        "selected_fy": fy, "selected_month": sel_month,
    }
    return templates.TemplateResponse(request, "partials/cih_filters.html", ctx)


@router.get("/cash-in-hand/data")
async def cash_in_hand_data(fy: int, month: int):
    db = await get_db()
    calendar_year = tx_svc.fy_to_calendar(fy, month)
    txns = await cash_svc.list_transactions(db, calendar_year, month)
    return JSONResponse(txns)


@router.get("/cash-in-hand/summary")
async def cash_in_hand_summary(fy: int, month: int):
    db = await get_db()
    calendar_year = tx_svc.fy_to_calendar(fy, month)
    summary = await cash_svc.get_summary(db, calendar_year, month)
    month_label = f"{month_abbr[month]} {calendar_year}"
    return JSONResponse({
        "total_debit": summary["total_debit"],
        "total_credit": summary["total_credit"],
        "txn_count": summary["txn_count"],
        "month_label": month_label,
    })


@router.get("/cash-in-hand/categories")
async def cash_in_hand_categories():
    db = await get_db()
    categories = await tx_svc.list_categories_for_transactions(db)
    return JSONResponse(categories)


@router.post("/cash-in-hand")
async def cash_in_hand_create(request: Request):
    db = await get_db()
    try:
        body = await request.json()
        data = CashInHandCreate(**body)
    except Exception:
        raise HTTPException(400, "Invalid input. Please check all required fields.")
    try:
        txn = await cash_svc.create_transaction(db, data.model_dump())
    except Exception as e:
        logger.exception("Failed to create cash-in-hand transaction")
        raise HTTPException(400, str(e))
    return JSONResponse(txn)


@router.put("/cash-in-hand/{txn_id}")
async def cash_in_hand_update(txn_id: int, request: Request):
    db = await get_db()
    try:
        body = await request.json()
        data = CashInHandUpdate(**body)
    except Exception:
        raise HTTPException(400, "Invalid input.")
    txn = await cash_svc.update_transaction(db, txn_id, data.model_dump(exclude_unset=True))
    if not txn:
        raise HTTPException(404, "Transaction not found")
    return JSONResponse(txn)


@router.delete("/cash-in-hand/{txn_id}")
async def cash_in_hand_delete(txn_id: int):
    db = await get_db()
    deleted = await cash_svc.delete_transaction(db, txn_id)
    if not deleted:
        raise HTTPException(404, "Transaction not found")
    return JSONResponse({"deleted": True})
