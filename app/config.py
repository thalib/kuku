import os
import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

APP_NAME = "Kuku"
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DB_PATH = os.getenv("DB_PATH", "kuku.db")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Kuku")
APP_ROOT_PATH = os.getenv("APP_ROOT_PATH", "")

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
            {"name": "Accounts", "url": "/banks/accounts", "icon": "bi-bank"},
            {"name": "Transaction", "url": "/banks/transactions", "icon": "bi-arrow-left-right"},
            {"name": "Cash in Hand", "url": "/banks/cash-in-hand", "icon": "bi-cash-coin"},
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
    {
        "label": "ADMIN",
        "links": [
            {"name": "Backup", "url": "/backup", "icon": "bi-download"},
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
    logger.info("=" * 40)
    logger.info("Active Configuration:")
    logger.info("=" * 40)
    for key, value in config_values.items():
        logger.info(f"{key} = {value}")
    logger.info("=" * 40)