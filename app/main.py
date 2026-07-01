from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.config import APP_NAME, APP_ROOT_PATH, ALLOWED_HOSTS, ALLOWED_HOSTS
from app.database import init_db, close_db
from app.routers import backup, bank_accounts, bank_transactions, cash_in_hand, categories, rules, dashboard, reports
from app.utils.templates import templates
import os


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield
    await close_db()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response


app = FastAPI(title="Kuku", lifespan=lifespan, root_path=APP_ROOT_PATH)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

_static_dir = os.path.join(os.path.dirname(__file__), "static")

app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(bank_accounts.router, prefix="/banks", tags=["Bank Accounts"])
app.include_router(bank_transactions.router, prefix="/banks", tags=["Transactions"])
app.include_router(cash_in_hand.router, prefix="/banks", tags=["Cash in Hand"])
app.include_router(categories.router, prefix="/banks", tags=["Categories"])
app.include_router(rules.router, prefix="/banks", tags=["Rules"])
app.include_router(reports.router, tags=["Reports"])
app.include_router(backup.router, tags=["Backup"])
