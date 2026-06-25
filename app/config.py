APP_NAME = "Kuku"
APP_HOST = "127.0.0.1"
APP_PORT = 8000
DB_PATH = "kuku.db"

NAV_GROUPS = [
    {
        "label": "Workspace",
        "links": [
            {"name": "Dashboard", "url": "/", "icon": "bi-speedometer2"},
        ],
    },
    {
        "label": "Items",
        "links": [
            {"name": "Categories", "url": "#", "icon": "bi-tags"},
            {"name": "Products", "url": "#", "icon": "bi-box-seam"},
            {"name": "Inventory", "url": "#", "icon": "bi-clipboard-data"},
        ],
    },
    {
        "label": "Sales",
        "links": [
            {"name": "Customers", "url": "#", "icon": "bi-people"},
            {"name": "Estimates", "url": "#", "icon": "bi-receipt"},
            {"name": "Invoices", "url": "#", "icon": "bi-bag-check"},
            {"name": "Payments", "url": "#", "icon": "bi-cash-coin"},
        ],
    },
    {
        "label": "Purchase",
        "links": [
            {"name": "Vendors", "url": "#", "icon": "bi-truck"},
            {"name": "Purchase Orders", "url": "#", "icon": "bi-file-earmark-text"},
            {"name": "Bills", "url": "#", "icon": "bi-receipt-cutoff"},
        ],
    },
    {
        "label": "Admin",
        "links": [
            {"name": "Settings", "url": "#", "icon": "bi-gear"},
            {"name": "Branch", "url": "#", "icon": "bi-diagram-3"},
            {"name": "Import / Export", "url": "#", "icon": "bi-arrow-left-right"},
            {"name": "Collections", "url": "#", "icon": "bi-table"},
        ],
    },
]

QUICK_LINKS = [
    {"name": "Invoices", "url": "#", "color": "dark"},
    {"name": "Estimates", "url": "#", "color": "dark"},
    {"name": "Payments", "url": "#", "color": "dark"},
    {"name": "Customers", "url": "#", "color": "dark"},
    {"name": "Products", "url": "#", "color": "primary"},
    {"name": "Inventory", "url": "#", "color": "primary"},
    {"name": "Categories", "url": "#", "color": "primary"},
    {"name": "Vendors", "url": "#", "color": "success"},
    {"name": "Purchase Orders", "url": "#", "color": "success"},
    {"name": "Bills", "url": "#", "color": "success"},
]
