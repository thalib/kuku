from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from app.config import APP_NAME, NAV_GROUPS
from app.database import get_db
from app.services import bank_accounts as bank_svc
from app.models.bank_accounts import BankAccountCreate
from app.utils.nav import mark_active_nav
from app.utils.templates import templates

router = APIRouter()


@router.get("/manage", response_class=HTMLResponse)
async def banks_manage(request: Request):
    db = await get_db()
    accounts = await bank_svc.list_accounts(db)
    return templates.TemplateResponse(
        request,
        "pages/banks_manage.html",
        {
            "app_name": APP_NAME,
            "page_title": "Bank Accounts - Kuku",
            "nav_groups": mark_active_nav(NAV_GROUPS, "/banks/manage"),
            "accounts": accounts,
        },
    )


@router.get("/accounts/form", response_class=HTMLResponse)
async def account_form(request: Request):
    return templates.TemplateResponse(
        request, "partials/bank_account_form.html", {"app_name": APP_NAME}
    )


@router.post("/accounts", response_class=HTMLResponse)
async def account_create(
    request: Request,
    bank_name: str = Form(...),
    account_name: str = Form(...),
    account_number: str = Form(...),
    ifsc_code: str = Form(...),
    branch_name: str = Form(""),
    notes: str = Form(""),
):
    try:
        data = BankAccountCreate(
            bank_name=bank_name,
            account_name=account_name,
            account_number=account_number,
            ifsc_code=ifsc_code,
            branch_name=branch_name or None,
            notes=notes or None,
        )
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "partials/bank_account_form.html",
            {"app_name": APP_NAME, "errors": ["Invalid input. Please check all required fields."]},
        )
    db = await get_db()
    await bank_svc.create_account(db, data)
    accounts = await bank_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/bank_account_list.html", {"accounts": accounts}
    )


@router.patch("/accounts/{account_id}/toggle", response_class=HTMLResponse)
async def account_toggle(request: Request, account_id: int):
    db = await get_db()
    account = await bank_svc.toggle_account(db, account_id)
    if not account:
        raise HTTPException(404)
    accounts = await bank_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/bank_account_list.html", {"accounts": accounts}
    )


@router.delete("/accounts/{account_id}", response_class=HTMLResponse)
async def account_delete(request: Request, account_id: int):
    db = await get_db()
    account = await bank_svc.get_account(db, account_id)
    if not account:
        raise HTTPException(404)
    if account.get("is_system", 0):
        return JSONResponse(
            {"error": "System bank accounts cannot be deleted."},
            status_code=403,
        )
    txn_count = await bank_svc.count_transactions(db, account_id)
    if txn_count > 0:
        return JSONResponse(
            {"error": f"This bank account has {txn_count} transaction(s). Delete all transactions before deleting the account."},
            status_code=409,
        )
    deleted = await bank_svc.delete_account(db, account_id)
    if not deleted:
        raise HTTPException(404)
    accounts = await bank_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/bank_account_list.html", {"accounts": accounts}
    )


@router.get("/accounts/{account_id}/check-delete")
async def account_check_delete(account_id: int):
    db = await get_db()
    account = await bank_svc.get_account(db, account_id)
    if not account:
        raise HTTPException(404)
    if account.get("is_system", 0):
        return {
            "can_delete": False,
            "txn_count": 0,
            "message": "System bank accounts cannot be deleted.",
        }
    txn_count = await bank_svc.count_transactions(db, account_id)
    if txn_count > 0:
        return {
            "can_delete": False,
            "txn_count": txn_count,
            "message": f"This bank account has {txn_count} transaction(s). Delete all transactions before deleting the account.",
        }
    return {"can_delete": True, "txn_count": 0, "message": ""}


@router.get("/accounts/clear-form", response_class=HTMLResponse)
async def account_clear_form(request: Request):
    return templates.TemplateResponse(request, "partials/bank_account_form_clear.html", {})


@router.get("/accounts/{account_id}/edit", response_class=HTMLResponse)
async def account_edit_form(request: Request, account_id: int):
    db = await get_db()
    account = await bank_svc.get_account(db, account_id)
    if not account:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "partials/bank_account_form.html", {"app_name": APP_NAME, "account": account}
    )


@router.post("/accounts/{account_id}/update", response_class=HTMLResponse)
async def account_update(
    request: Request,
    account_id: int,
    bank_name: str = Form(...),
    account_name: str = Form(...),
    account_number: str = Form(...),
    ifsc_code: str = Form(...),
    branch_name: str = Form(""),
    notes: str = Form(""),
):
    db = await get_db()
    try:
        updated = await bank_svc.update_account(
            db,
            account_id,
            {
                "bank_name": bank_name,
                "account_name": account_name,
                "account_number": account_number,
                "ifsc_code": ifsc_code,
                "branch_name": branch_name or None,
                "notes": notes or None,
            },
        )
    except Exception:
        return templates.TemplateResponse(
            request,
            "partials/bank_account_form.html",
            {"app_name": APP_NAME, "account": await bank_svc.get_account(db, account_id), "errors": ["Invalid input."]},
        )
    if not updated:
        raise HTTPException(404)
    accounts = await bank_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/bank_account_list.html", {"accounts": accounts}
    )
