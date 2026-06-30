from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.config import APP_NAME, NAV_GROUPS
from app.database import get_db
from app.services import categories as cat_svc
from app.services import rules as rule_svc
from app.services import bank_accounts as acc_svc
from app.models.rules import RuleCreate, RuleUpdate
from app.utils.nav import mark_active_nav
from app.utils.templates import templates

router = APIRouter()


def _base_ctx(request: Request):
    return {
        "app_name": APP_NAME,
        "page_title": "Classification Rules - Kuku",
        "nav_groups": mark_active_nav(NAV_GROUPS, "/banks/rules"),
    }


@router.get("/rules", response_class=HTMLResponse)
async def rules_page(request: Request):
    db = await get_db()
    rules = await rule_svc.list_rules(db)
    categories = await cat_svc.list_categories(db)
    accounts = await acc_svc.list_accounts(db)
    ctx = _base_ctx(request)
    ctx["rules"] = rules
    ctx["categories"] = categories
    ctx["accounts"] = accounts
    return templates.TemplateResponse(request, "pages/banks_rules.html", ctx)


@router.get("/rules/form", response_class=HTMLResponse)
async def rule_form(request: Request):
    db = await get_db()
    categories = await cat_svc.list_categories(db)
    accounts = await acc_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/rule_form.html",
        {"app_name": APP_NAME, "categories": categories, "accounts": accounts},
    )


@router.get("/rules/clear-form", response_class=HTMLResponse)
async def rule_clear_form(request: Request):
    return templates.TemplateResponse(request, "partials/rule_form_clear.html", {})


@router.get("/rules/{rule_id}/edit", response_class=HTMLResponse)
async def rule_edit_form(request: Request, rule_id: int):
    db = await get_db()
    rule = await rule_svc.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(404)
    categories = await cat_svc.list_categories(db)
    accounts = await acc_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/rule_form.html",
        {"app_name": APP_NAME, "rule": rule, "categories": categories, "accounts": accounts},
    )


@router.post("/rules", response_class=HTMLResponse)
async def rule_create(
    request: Request,
    search_text: str = Form(...),
    match_type: str = Form(...),
    category_id: str = Form(...),
    priority: str = Form("0"),
    applies_to: str = Form("both"),
    is_active: str = Form("on"),
    account_id: str = Form(""),
):
    try:
        data = RuleCreate(
            search_text=search_text,
            match_type=match_type,
            category_id=int(category_id),
            priority=int(priority) if priority else 0,
            applies_to=applies_to,
            is_active=(is_active == "on"),
            account_id=int(account_id) if account_id else None,
        )
    except (ValidationError, ValueError):
        return templates.TemplateResponse(
            request, "partials/rule_form.html",
            {
                "app_name": APP_NAME,
                "categories": await cat_svc.list_categories(await get_db()),
                "accounts": await acc_svc.list_accounts(await get_db()),
                "errors": ["Invalid input. Please check all required fields."],
                "form_search_text": search_text,
                "form_match_type": match_type,
                "form_category_id": category_id,
                "form_priority": priority,
                "form_applies_to": applies_to,
                "form_is_active": (is_active == "on"),
                "form_account_id": account_id,
            },
        )
    db = await get_db()
    await rule_svc.create_rule(db, data)
    rules = await rule_svc.list_rules(db)
    accounts = await acc_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/rule_list.html", {"rules": rules, "categories": await cat_svc.list_categories(db), "accounts": accounts}
    )


@router.post("/rules/{rule_id}/update", response_class=HTMLResponse)
async def rule_update(
    request: Request,
    rule_id: int,
    search_text: str = Form(...),
    match_type: str = Form(...),
    category_id: str = Form(...),
    priority: str = Form("0"),
    applies_to: str = Form("both"),
    is_active: str = Form("on"),
    account_id: str = Form(""),
):
    try:
        data = RuleUpdate(
            search_text=search_text,
            match_type=match_type,
            category_id=int(category_id),
            priority=int(priority) if priority else 0,
            applies_to=applies_to,
            is_active=(is_active == "on"),
            account_id=int(account_id) if account_id else None,
        )
        if not account_id:
            data._clear_account_id = True
    except (ValueError, ValidationError):
        raise HTTPException(400, "Invalid input")
    db = await get_db()
    updated = await rule_svc.update_rule(db, rule_id, data)
    if not updated:
        raise HTTPException(404)
    rules = await rule_svc.list_rules(db)
    accounts = await acc_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/rule_list.html", {"rules": rules, "categories": await cat_svc.list_categories(db), "accounts": accounts}
    )


@router.patch("/rules/{rule_id}/toggle", response_class=HTMLResponse)
async def rule_toggle(request: Request, rule_id: int):
    db = await get_db()
    updated = await rule_svc.toggle_rule(db, rule_id)
    if not updated:
        raise HTTPException(404)
    rules = await rule_svc.list_rules(db)
    accounts = await acc_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/rule_list.html", {"rules": rules, "categories": await cat_svc.list_categories(db), "accounts": accounts}
    )


@router.delete("/rules/{rule_id}", response_class=HTMLResponse)
async def rule_delete(request: Request, rule_id: int):
    db = await get_db()
    deleted = await rule_svc.delete_rule(db, rule_id)
    if not deleted:
        raise HTTPException(404)
    rules = await rule_svc.list_rules(db)
    accounts = await acc_svc.list_accounts(db)
    return templates.TemplateResponse(
        request, "partials/rule_list.html", {"rules": rules, "categories": await cat_svc.list_categories(db), "accounts": accounts}
    )
