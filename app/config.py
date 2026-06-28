import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

APP_NAME = "Kuku"
APP_HOST = "127.0.0.1"
APP_PORT = 8000
DB_PATH = "kuku.db"
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
            {"name": "Reports", "url": "/reports", "icon": "bi-bar-chart"},
        ],
    },

]
