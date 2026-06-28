import os
from abc import ABC, abstractmethod
from calendar import month_abbr
from typing import Any

from jinja2 import Environment, FileSystemLoader

from app.config import COMPANY_NAME

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates", "exports")
_jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)


def get_company_name() -> str:
    return COMPANY_NAME


def build_account_label(account: dict | None, account_id: int) -> str:
    if account:
        return f"{account['bank_name']} - {account['account_number']}"
    return f"Account #{account_id}"


def build_category_display(txn: dict) -> str:
    cat_type = txn.get("cat_type")
    cat_name = txn.get("cat_name")
    if cat_type and cat_name:
        return f"{cat_type}:{cat_name}"
    return cat_name or ""


def build_month_label(calendar_year: int, month: int) -> str:
    return f"{month_abbr[month]} {calendar_year}"


def get_template(domain: str, fmt: str) -> Any:
    return _jinja_env.get_template(f"{domain}/{fmt}")


class BaseExporter(ABC):
    domain: str = ""

    def __init__(self, account: dict | None = None, account_id: int = 0):
        self.account = account
        self.account_id = account_id
        self.company_name = get_company_name()
        self.account_label = build_account_label(account, account_id)

    @property
    def base_context(self) -> dict:
        return {
            "company_name": self.company_name,
            "account_label": self.account_label,
        }

    @abstractmethod
    def render_csv(self, **kwargs) -> bytes:
        ...

    @abstractmethod
    def render_xlsx(self, **kwargs) -> bytes:
        ...

    @abstractmethod
    def render_pdf(self, **kwargs) -> bytes:
        ...

    def filename(self, fy: int, month: int, ext: str) -> str:
        return f"{self.domain}_{self.account_id}_{fy}_{month:02d}.{ext}"
