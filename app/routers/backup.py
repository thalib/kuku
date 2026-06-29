from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import json
import io

from app.config import APP_NAME, NAV_GROUPS
from app.database import get_db
from app.services import backup as backup_svc
from app.utils.nav import mark_active_nav
from app.utils.templates import templates

router = APIRouter()


@router.get("/backup", response_class=HTMLResponse)
async def backup_page(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/backup.html",
        {
            "app_name": APP_NAME,
            "page_title": "Backup & Restore - Kuku",
            "nav_groups": mark_active_nav(NAV_GROUPS, "/backup"),
        },
    )


@router.get("/backup/export")
async def backup_export():
    db = await get_db()
    data = await backup_svc.export_data(db)
    return StreamingResponse(
        io.BytesIO(data.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=kuku-backup.json"},
    )


@router.post("/backup/import", response_class=HTMLResponse)
async def backup_import(request: Request, file: UploadFile = Form(...)):
    db = await get_db()
    try:
        raw = await file.read()
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return templates.TemplateResponse(
            request,
            "pages/backup.html",
            {
                "app_name": APP_NAME,
                "page_title": "Backup & Restore - Kuku",
                "nav_groups": mark_active_nav(NAV_GROUPS, "/backup"),
                "error": "Invalid backup file. Please upload a valid Kuku backup JSON file.",
            },
        )
    try:
        stats = await backup_svc.import_data(db, payload)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "pages/backup.html",
            {
                "app_name": APP_NAME,
                "page_title": "Backup & Restore - Kuku",
                "nav_groups": mark_active_nav(NAV_GROUPS, "/backup"),
                "error": str(exc),
            },
        )
    return templates.TemplateResponse(
        request,
        "pages/backup.html",
        {
            "app_name": APP_NAME,
            "page_title": "Backup & Restore - Kuku",
            "nav_groups": mark_active_nav(NAV_GROUPS, "/backup"),
            "stats": stats,
        },
    )
