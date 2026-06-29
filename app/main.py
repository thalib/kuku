from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from app.config import APP_NAME
from app.database import init_db, close_db
from app.routers import bank_accounts, bank_transactions, categories, rules, dashboard, reports
import os


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Kuku", lifespan=lifespan)

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
