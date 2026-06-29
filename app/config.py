import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

APP_NAME = "Kuku"
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DB_PATH = os.getenv("DB_PATH", "kuku.db")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Kuku")

NAV_GROUPS = [
    {
        "label": None,
        "links": [
            {"name": "Dashboard", "url": "/", "icon": "bi-speedometer2"},
        ],
    },
    {
        "label": "BANKS",
        "links": [
            {"name": "Manage", "url": "/banks/manage", "icon": "bi-bank"},
            {"name": "Transaction", "url": "/banks/transactions", "icon": "bi-arrow-left-right"},
            {"name": "Categories", "url": "/banks/categories", "icon": "bi-tags"},
            {"name": "Rules", "url": "/banks/rules", "icon": "bi-funnel"},
        ],
    },
    {
        "label": "REPORTS",
        "links": [
            {"name": "Profit & Loss", "url": "/reports/profit-loss", "icon": "bi-graph-up"},
            {"name": "Balance Sheet", "url": "/reports/balance-sheet", "icon": "bi-file-earmark-bar-graph"},
            {"name": "Cash Flow", "url": "/reports/cash-flow", "icon": "bi-cash-stack"},
        ],
    },

]


def print_config():
    config_values = {
        "APP_NAME": APP_NAME,
        "APP_HOST": APP_HOST,
        "APP_PORT": APP_PORT,
        "DB_PATH": DB_PATH,
        "COMPANY_NAME": COMPANY_NAME,
    }
    print("=" * 40)
    print("Active Configuration:")
    print("=" * 40)
    for key, value in config_values.items():
        print(f"{key} = {value}")
    print("=" * 40)