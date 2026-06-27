APP_NAME = "Kuku"
APP_HOST = "127.0.0.1"
APP_PORT = 8000
DB_PATH = "kuku.db"

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
        ],
    },
    {
        "label": "REPORTS",
        "links": [
            {"name": "Reports", "url": "/reports", "icon": "bi-bar-chart"},
        ],
    },
    {
        "label": "ADMIN",
        "links": [
            {"name": "Settings", "url": "/settings", "icon": "bi-gear"},
        ],
    },
]
