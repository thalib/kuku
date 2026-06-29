import json
import logging
from calendar import month_abbr
from datetime import date

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import ValidationError

from app.config import APP_NAME, NAV_GROUPS
from app.database import get_db
from app.services import bank_accounts as bank_svc
from app.services import transactions as tx_svc
from app.services import exports as export_svc
from app.models.transactions import TransactionUpdate, TransactionCategoryUpdate
from app.utils.nav import mark_active_nav
from app.utils.templates import templates

router = APIRouter()

logger = logging.getLogger(__name__)

MONTHS = [
    (1, "JAN"), (2, "FEB"), (3, "MAR"), (4, "APR"),
    (5, "MAY"), (6, "JUN"), (7, "JUL"), (8, "AUG"),
    (9, "SEP"), (10, "OCT"), (11, "NOV"), (12, "DEC"),
]


def _base_ctx(request: Request, page_url: str, page_name: str):
    return {
        "app_name": APP_NAME,
        "page_title": f"{page_name} - Kuku",
        "nav_groups": mark_active_nav(NAV_GROUPS, page_url),
    }


@router.get("/transactions", response_class=HTMLResponse)
async def transactions_page(request: Request):
    db = await get_db()
    accounts = await bank_svc.list_accounts(db)
    active_accounts = [a for a in accounts if a["is_active"]]
    ctx = _base_ctx(request, "/banks/transactions", "Transactions")
    ctx["accounts"] = active_accounts
    return templates.TemplateResponse(request, "pages/banks_transactions.html", ctx)


@router.get("/transactions/filters", response_class=HTMLResponse)
async def transactions_filters(request: Request, account_id: int, selected_fy: int | None = None, selected_month: int | None = None):
    db = await get_db()
    fy_years = await tx_svc.get_available_fy_years(db, account_id)
    if not fy_years:
        ctx = {"no_data": True, "account_id": account_id}
        return templates.TemplateResponse(request, "partials/tx_filters.html", ctx)
    now = date.today()
    current_fy = now.year if now.month >= 4 else now.year - 1
    fy = selected_fy if selected_fy and selected_fy in fy_years else current_fy if current_fy in fy_years else max(fy_years)
    avail = await tx_svc.get_available_months(db, account_id, fy)
    months = [(m, f"{MONTHS[m - 1][1]} {tx_svc.fy_to_calendar(fy, m)}") for m in avail]
    sel_month = selected_month if selected_month and selected_month in avail else max(avail)
    ctx = {
        "no_data": False, "account_id": account_id,
        "fy_years": fy_years, "months": months,
        "selected_fy": fy, "selected_month": sel_month,
    }
    return templates.TemplateResponse(request, "partials/tx_filters.html", ctx)


@router.get("/transactions/table", response_class=HTMLResponse)
async def transactions_table(request: Request, account_id: int, fy: int, month: int):
    db = await get_db()
    calendar_year = tx_svc.fy_to_calendar(fy, month)
    txns = await tx_svc.list_transactions(db, account_id, calendar_year, month)
    categories = await tx_svc.list_categories_for_transactions(db)
    summary = await tx_svc.get_summary(db, account_id, calendar_year, month)
    account = await bank_svc.get_account(db, account_id)
    month_label = f"{month_abbr[month]} {calendar_year}"
    ctx = {
        "transactions": txns,
        "categories": categories,
        "summary": summary,
        "account": account,
        "account_id": account_id,
        "fy": fy,
        "month": month,
        "month_label": month_label,
    }
    return templates.TemplateResponse(request, "partials/tx_table.html", ctx)


@router.get("/transactions/import/form", response_class=HTMLResponse)
async def import_form(request: Request, account_id: int):
    return templates.TemplateResponse(
        request, "partials/tx_import_form.html", {"account_id": account_id}
    )


@router.post("/transactions/import/preview", response_class=HTMLResponse)
async def import_preview(request: Request, account_id: int = Form(...), file: UploadFile = File(...)):
    if file.size and file.size > 10 * 1024 * 1024:
        return templates.TemplateResponse(
            request, "partials/tx_import_preview.html",
            {"error": "File size exceeds 10MB limit.", "transactions": [], "account_id": account_id, "count": 0},
        )
    
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        if ext == "csv":
            content = (await file.read()).decode("utf-8-sig")
            txns = tx_svc.parse_csv_rows(content)
        elif ext in ("xls", "xlsx"):
            data = await file.read()
            txns = tx_svc.parse_excel_bytes(data, filename)
        else:
            content = (await file.read()).decode("utf-8-sig")
            txns = tx_svc.parse_csv_rows(content)
    except Exception as e:
        logger.exception("File parse error during import preview")
        return templates.TemplateResponse(
            request, "partials/tx_import_preview.html",
            {"error": "Failed to parse file. Please check the format and try again.", "transactions": [], "account_id": account_id, "count": 0},
        )

    if not txns:
        return templates.TemplateResponse(
            request, "partials/tx_import_preview.html",
            {"error": "No valid transactions found in file.", "transactions": [], "account_id": account_id, "count": 0},
        )
    
    db = await get_db()
    category_map = await tx_svc.get_category_name_map(db)
    
    unresolved_categories = set()
    hashes = set()
    for txn in txns:
        if "category" in txn and txn["category"]:
            if txn["category"] not in category_map:
                unresolved_categories.add(txn["category"])
                txn["category_unresolved"] = True
        hashes.add(tx_svc.compute_txn_hash(txn))
    
    existing_hashes = await tx_svc.find_existing_txn_hashes(db, account_id, hashes)
    duplicate_count = 0
    for txn in txns:
        h = tx_svc.compute_txn_hash(txn)
        txn["is_duplicate"] = h in existing_hashes
        if txn["is_duplicate"]:
            duplicate_count += 1
    has_unresolved = len(unresolved_categories) > 0

    return templates.TemplateResponse(
        request, "partials/tx_import_preview.html",
        {
            "transactions": txns,
            "account_id": account_id,
            "error": None,
            "count": len(txns),
            "duplicate_count": duplicate_count,
            "has_categories": any("category" in t for t in txns),
            "unresolved_categories": sorted(list(unresolved_categories)) if unresolved_categories else None,
        },
    )


@router.post("/transactions/import/confirm", response_class=HTMLResponse)
async def import_confirm(request: Request, account_id: int = Form(...), data: str = Form(...)):
    db = await get_db()
    try:
        txns = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid transaction data")
    
    uncategorized_ids = await tx_svc.get_uncategorized_category_ids(db)
    category_map = await tx_svc.get_category_name_map(db)
    
    unresolved_categories = set()
    for txn in txns:
        if "category" in txn and txn["category"]:
            if txn["category"] in category_map:
                txn["category_id"] = category_map[txn["category"]]
            else:
                unresolved_categories.add(txn["category"])
                if txn.get("debit", 0) > 0 and txn.get("credit", 0) == 0:
                    txn["category_id"] = uncategorized_ids.get("Expense")
                elif txn.get("credit", 0) > 0 and txn.get("debit", 0) == 0:
                    txn["category_id"] = uncategorized_ids.get("Income")
                else:
                    txn["category_id"] = None
        else:
            if txn.get("debit", 0) > 0 and txn.get("credit", 0) == 0:
                txn["category_id"] = uncategorized_ids.get("Expense")
            elif txn.get("credit", 0) > 0 and txn.get("debit", 0) == 0:
                txn["category_id"] = uncategorized_ids.get("Income")
            else:
                txn["category_id"] = None
    
    result = await tx_svc.bulk_create_transactions(db, account_id, txns, skip_existing=True)
    count = result["count"]
    skipped = result["skipped"]

    dates = [t["txn_date"] for t in txns if t.get("txn_date")]
    if dates:
        latest_date = max(dates)
        d = date.fromisoformat(latest_date)
        fy, month = tx_svc.date_to_fy_start(d.year, d.month), d.month
    else:
        now = date.today()
        fy, month = tx_svc.date_to_fy_start(now.year, now.month), now.month

    resp_data = {"fy": fy, "month": month, "count": count, "skipped": skipped}
    if unresolved_categories:
        resp_data["unresolved_categories"] = sorted(list(unresolved_categories))
    
    resp = HTMLResponse("")
    resp.headers["HX-Trigger"] = json.dumps({"txImported": resp_data})
    return resp


@router.get("/transactions/{txn_id}/edit", response_class=HTMLResponse)
async def transaction_edit_form(request: Request, txn_id: int):
    db = await get_db()
    txn = await tx_svc.get_transaction_with_category(db, txn_id)
    if not txn:
        raise HTTPException(404)
    categories = await tx_svc.list_categories_for_transactions(db)
    return templates.TemplateResponse(
        request, "partials/tx_edit_form.html", {"txn": txn, "categories": categories}
    )


@router.get("/transactions/{txn_id}/cancel", response_class=HTMLResponse)
async def transaction_cancel_edit(request: Request, txn_id: int):
    db = await get_db()
    txn = await tx_svc.get_transaction_with_category(db, txn_id)
    if not txn:
        raise HTTPException(404)
    categories = await tx_svc.list_categories_for_transactions(db)
    return templates.TemplateResponse(
        request, "partials/tx_row.html", {"txn": txn, "categories": categories}
    )


@router.post("/transactions/{txn_id}/update", response_class=HTMLResponse)
async def transaction_update(
    request: Request,
    txn_id: int,
    txn_date: str = Form(...),
    value_date: str = Form(...),
    narration: str = Form(""),
    reference: str = Form(""),
    debit: str = Form("0"),
    credit: str = Form("0"),
    balance: str = Form("0"),
    category_id: str = Form(""),
):
    db = await get_db()
    try:
        update_data = TransactionUpdate(
            txn_date=date.fromisoformat(txn_date),
            value_date=date.fromisoformat(value_date),
            narration=narration or None,
            reference=reference or None,
            debit=float(debit) if debit else 0,
            credit=float(credit) if credit else 0,
            balance=float(balance) if balance else 0,
            category_id=int(category_id) if category_id else None,
        )
    except (ValueError, ValidationError):
        raise HTTPException(400, "Invalid data")
    updated = await tx_svc.update_transaction(db, txn_id, update_data)
    if not updated:
        raise HTTPException(404)
    txn = await tx_svc.get_transaction_with_category(db, txn_id)
    categories = await tx_svc.list_categories_for_transactions(db)
    return templates.TemplateResponse(
        request, "partials/tx_row.html", {"txn": txn, "categories": categories}
    )


@router.patch("/transactions/{txn_id}/category", response_class=HTMLResponse)
async def transaction_update_category(
    request: Request, txn_id: int, category_id: int = Form(...),
):
    db = await get_db()
    updated = await tx_svc.update_transaction_category(db, txn_id, category_id)
    if not updated:
        raise HTTPException(404)
    return HTMLResponse("", status_code=200)


@router.delete("/transactions/{txn_id}", response_class=HTMLResponse)
async def transaction_delete(request: Request, txn_id: int):
    db = await get_db()
    deleted = await tx_svc.delete_transaction(db, txn_id)
    if not deleted:
        raise HTTPException(404)
    return HTMLResponse("", status_code=200, headers={"HX-Trigger": "txDeleted"})


@router.post("/transactions/rules/run", response_class=JSONResponse)
async def run_rules(account_id: int = Form(...), fy: int = Form(...), month: int = Form(...)):
    db = await get_db()
    calendar_year = tx_svc.fy_to_calendar(fy, month)
    updated = await tx_svc.apply_rules_to_transactions(db, account_id, calendar_year, month)
    return JSONResponse({"updated": updated})


@router.get("/transactions/bulk/summary")
async def bulk_delete_summary(account_id: int, fy: int, month: int):
    db = await get_db()
    calendar_year = tx_svc.fy_to_calendar(fy, month)
    summary = await tx_svc.get_month_summary(db, account_id, calendar_year, month)
    month_label = f"{month_abbr[month]} {calendar_year} (FY {fy}-{fy + 1})"
    return JSONResponse({
        "count": summary["txn_count"],
        "total_debit": summary["total_debit"],
        "total_credit": summary["total_credit"],
        "month_label": month_label,
    })


@router.delete("/transactions/bulk/delete")
async def bulk_delete_execute(account_id: int, fy: int, month: int):
    db = await get_db()
    calendar_year = tx_svc.fy_to_calendar(fy, month)
    deleted = await tx_svc.delete_transactions_by_month(db, account_id, calendar_year, month)
    return JSONResponse({"deleted": deleted})



@router.get("/transactions/export/csv")
async def export_csv(account_id: int, fy: int, month: int):
    db = await get_db()
    calendar_year = tx_svc.fy_to_calendar(fy, month)
    txns = await tx_svc.list_transactions(db, account_id, calendar_year, month)
    summary = await tx_svc.get_summary(db, account_id, calendar_year, month)
    account = await bank_svc.get_account(db, account_id)

    exporter = export_svc.TransactionExporter(account, account_id, fy, calendar_year, month)
    content = exporter.render_csv(txns, summary)
    fname = exporter.filename(calendar_year, month, "csv")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/transactions/export/xlsx")
async def export_xlsx(account_id: int, fy: int, month: int):
    db = await get_db()
    calendar_year = tx_svc.fy_to_calendar(fy, month)
    txns = await tx_svc.list_transactions(db, account_id, calendar_year, month)
    summary = await tx_svc.get_summary(db, account_id, calendar_year, month)
    account = await bank_svc.get_account(db, account_id)

    exporter = export_svc.TransactionExporter(account, account_id, fy, calendar_year, month)
    content = exporter.render_xlsx(txns, summary)
    fname = exporter.filename(calendar_year, month, "xlsx")
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/transactions/export/pdf")
async def export_pdf(account_id: int, fy: int, month: int):
    db = await get_db()
    calendar_year = tx_svc.fy_to_calendar(fy, month)
    txns = await tx_svc.list_transactions(db, account_id, calendar_year, month)
    summary = await tx_svc.get_summary(db, account_id, calendar_year, month)
    account = await bank_svc.get_account(db, account_id)

    exporter = export_svc.TransactionExporter(account, account_id, fy, calendar_year, month)
    content = exporter.render_pdf(txns, summary)
    fname = exporter.filename(calendar_year, month, "pdf")
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
