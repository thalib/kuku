from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.config import APP_NAME
from app.database import init_db, close_db
from app.routers import bank_accounts, bank_transactions, categories, rules, dashboard, reports
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
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app = FastAPI(title="Kuku", lifespan=lifespan)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

_static_dir = os.path.join(os.path.dirname(__file__), "static")
_template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_template_dir)

app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(bank_accounts.router, prefix="/banks", tags=["Bank Accounts"])
app.include_router(bank_transactions.router, prefix="/banks", tags=["Transactions"])
app.include_router(categories.router, prefix="/banks", tags=["Categories"])
app.include_router(rules.router, prefix="/banks", tags=["Rules"])
app.include_router(reports.router, tags=["Reports"])
