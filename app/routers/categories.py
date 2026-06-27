from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
import os

from app.config import APP_NAME, NAV_GROUPS
from app.database import get_db
from app.services import categories as cat_svc
from app.models.categories import CategoryCreate, CategoryUpdate, CATEGORY_TYPES
from app.utils.nav import mark_active_nav

router = APIRouter()

_template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=_template_dir)


@router.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request):
    db = await get_db()
    cats = await cat_svc.list_categories(db)
    return templates.TemplateResponse(
        request,
        "pages/banks_categories.html",
        {
            "app_name": APP_NAME,
            "page_title": "Categories - Kuku",
            "nav_groups": mark_active_nav(NAV_GROUPS, "/banks/categories"),
            "categories": cats,
            "category_types": CATEGORY_TYPES,
        },
    )


@router.get("/categories/form", response_class=HTMLResponse)
async def category_form(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/category_form.html",
        {"app_name": APP_NAME, "category_types": CATEGORY_TYPES},
    )


@router.get("/categories/clear-form", response_class=HTMLResponse)
async def category_clear_form(request: Request):
    return templates.TemplateResponse(
        request, "partials/category_form_clear.html", {}
    )


@router.get("/categories/{category_id}/edit", response_class=HTMLResponse)
async def category_edit_form(request: Request, category_id: int):
    db = await get_db()
    cat = await cat_svc.get_category(db, category_id)
    if not cat:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request,
        "partials/category_form.html",
        {"app_name": APP_NAME, "category": cat, "category_types": CATEGORY_TYPES},
    )


@router.post("/categories", response_class=HTMLResponse)
async def category_create(
    request: Request,
    name: str = Form(...),
    type: str = Form(...),
    description: str = Form(""),
):
    try:
        data = CategoryCreate(
            name=name,
            type=type,
            description=description or None,
        )
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "partials/category_form.html",
            {
                "app_name": APP_NAME,
                "category_types": CATEGORY_TYPES,
                "errors": ["Invalid input. Please check all required fields."],
                "form_name": name,
                "form_type": type,
                "form_description": description,
            },
        )
    db = await get_db()
    await cat_svc.create_category(db, data)
    cats = await cat_svc.list_categories(db)
    return templates.TemplateResponse(
        request, "partials/category_list.html", {"categories": cats}
    )


@router.post("/categories/{category_id}/update", response_class=HTMLResponse)
async def category_update(
    request: Request,
    category_id: int,
    name: str = Form(...),
    type: str = Form(...),
    description: str = Form(""),
):
    try:
        data = CategoryUpdate(
            name=name,
            type=type,
            description=description or None,
        )
    except ValidationError:
        raise HTTPException(400, "Invalid input")
    db = await get_db()
    updated = await cat_svc.update_category(db, category_id, data)
    if not updated:
        raise HTTPException(404)
    cats = await cat_svc.list_categories(db)
    return templates.TemplateResponse(
        request, "partials/category_list.html", {"categories": cats}
    )


@router.delete("/categories/{category_id}", response_class=HTMLResponse)
async def category_delete(request: Request, category_id: int):
    db = await get_db()
    deleted = await cat_svc.delete_category(db, category_id)
    if not deleted:
        raise HTTPException(404)
    cats = await cat_svc.list_categories(db)
    return templates.TemplateResponse(
        request, "partials/category_list.html", {"categories": cats}
    )
