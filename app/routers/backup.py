import hashlib
import io
import json

from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, StreamingResponse

from app.config import APP_NAME, NAV_GROUPS
from app.database import get_db
from app.services import backup as backup_svc
from app.utils.nav import mark_active_nav
from app.utils.templates import templates

router = APIRouter()

_pending_backups: dict[str, dict] = {}


def _backup_ctx(request: Request, **extra) -> dict:
    ctx = {
        "app_name": APP_NAME,
        "page_title": "Backup & Restore - Kuku",
        "nav_groups": mark_active_nav(NAV_GROUPS, "/backup"),
    }
    ctx.update(extra)
    return ctx


def _make_token(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


@router.get("/backup", response_class=HTMLResponse)
async def backup_page(request: Request):
    return templates.TemplateResponse(request, "pages/backup.html", _backup_ctx(request))


@router.get("/backup/export")
async def backup_export():
    db = await get_db()
    data = await backup_svc.export_data(db)
    return StreamingResponse(
        io.BytesIO(data.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=kuku-backup.json"},
    )


def _parse_upload(raw: bytes) -> dict:
    decoded = raw.decode("utf-8")
    payload = json.loads(decoded)
    if not isinstance(payload, dict):
        raise ValueError("Backup file must be a JSON object.")
    return payload


@router.post("/backup/analyze", response_class=HTMLResponse)
async def backup_analyze(request: Request, file: UploadFile = Form(...)):
    try:
        raw = await file.read()
        payload = _parse_upload(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        return templates.TemplateResponse(
            request,
            "partials/backup_error.html",
            {"error": f"Invalid backup file: {exc}"},
        )

    db = await get_db()
    try:
        analysis = await backup_svc.analyze_backup(db, payload)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "partials/backup_error.html",
            {"error": str(exc)},
        )

    total_import = (
        len(analysis["accounts_to_import"])
        + len(analysis["categories_to_import"])
        + len(analysis["rules_to_import"])
    )
    total_skip = (
        len(analysis["accounts_to_skip"])
        + len(analysis["categories_to_skip"])
        + len(analysis["rules_to_skip"])
    )

    has_any_records = (
        len(analysis["accounts_to_import"])
        + len(analysis["accounts_to_skip"])
        + len(analysis["categories_to_import"])
        + len(analysis["categories_to_skip"])
        + len(analysis["rules_to_import"])
        + len(analysis["rules_to_skip"])
    )

    if has_any_records == 0:
        return templates.TemplateResponse(
            request,
            "partials/backup_error.html",
            {"error": "Backup file is empty. Nothing to import."},
        )

    if total_import == 0 and not analysis["errors"]:
        return templates.TemplateResponse(
            request,
            "partials/backup_error.html",
            {"error": "Nothing to import. All records in the backup already exist in the database."},
        )

    token = _make_token(payload)
    _pending_backups[token] = payload

    return templates.TemplateResponse(
        request,
        "partials/backup_preview.html",
        {
            "token": token,
            "analysis": analysis,
            "total_import": total_import,
            "total_skip": total_skip,
        },
    )


@router.post("/backup/import", response_class=HTMLResponse)
async def backup_import(request: Request, token: str = Form(...), sections: str = Form("all")):
    payload = _pending_backups.pop(token, None)
    if payload is None:
        return templates.TemplateResponse(
            request,
            "partials/backup_error.html",
            {"error": "Backup session expired. Please upload the file again."},
        )

    section_list = None
    if sections != "all":
        valid = {"accounts", "categories", "rules"}
        selected = [s.strip() for s in sections.split(",") if s.strip() in valid]
        if selected:
            section_list = selected

    db = await get_db()
    stats = await backup_svc.import_data(db, payload, sections=section_list)

    return templates.TemplateResponse(
        request,
        "partials/backup_result.html",
        {"stats": stats, "sections": section_list},
    )
