from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
import os

from app.config import APP_NAME, NAV_GROUPS
from app.database import get_db
from app.services import bank_accounts as bank_svc
from app.models.bank_accounts import BankAccountCreate
from app.utils.nav import mark_active_nav

router = APIRouter()

_template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=_template_dir)


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
    deleted = await bank_svc.delete_account(db, account_id)
    if not deleted:
        raise HTTPException(404)
    accounts = await bank_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/bank_account_list.html", {"accounts": accounts}
    )


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
