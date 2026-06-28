import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from app import config, database


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    config.DB_PATH = ":memory:"
    database._db = None
    await database.init_db()
    yield
    await database.close_db()


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestDashboardPage:

    def test_get_root_returns_200(self, client):
        assert client.get("/").status_code == 200

    def test_page_contains_kuku(self, client):
        assert "Kuku" in client.get("/").text

    def test_sidebar_groups_present(self, client):
        body = client.get("/").text
        for group in ["BANKS", "REPORTS"]:
            assert group in body, f"Sidebar missing group: {group}"

    def test_dashboard_active_nav_highlighted(self, client):
        body = client.get("/").text
        assert "bg-primary" in body
        assert "bi-speedometer2" in body

    def test_sidebar_toggle_button(self, client):
        body = client.get("/").text
        assert "sidebarToggle" in body

    def test_sidebar_wrap_id(self, client):
        body = client.get("/").text
        assert 'id="sidebarWrap"' in body

    def test_dashboard_htmx_loads_content(self, client):
        body = client.get("/").text
        assert 'hx-get="/content"' in body
        assert 'hx-trigger="load"' in body


class TestDashboardContent:

    def test_content_returns_200(self, client):
        assert client.get("/content").status_code == 200

    def test_content_shows_no_data_when_empty(self, client):
        body = client.get("/content").text
        assert "No transaction data available" in body

    def test_content_with_fy_shows_chart_sections(self, client):
        body = client.get("/content?fy=2025").text
        assert "chart-income-expense" in body
        assert "chart-top-income" in body
        assert "chart-top-expense" in body

    def test_content_contains_update_button(self, client):
        body = client.get("/content").text
        assert "dashboard-update" in body

    def test_content_contains_fy_select(self, client):
        body = client.get("/content").text
        assert "dashboard-fy-select" in body

    def test_content_contains_month_select(self, client):
        body = client.get("/content").text
        assert "dashboard-month-select" in body


class TestDashboardContentWithData:

    @pytest.fixture(autouse=True)
    def setup_data(self, client):
        self.client = client
        self._create_account()
        self._create_transactions()

    def _create_account(self):
        self.client.post("/banks/accounts", data={
            "bank_name": "Test Bank",
            "account_name": "Test Account",
            "account_number": "1234567890",
            "ifsc_code": "TEST0001",
        })

    def _create_transactions(self):
        from app.database import get_db
        from app.services.transactions import bulk_create_transactions
        import asyncio

        async def _seed():
            db = await get_db()
            txns = [
                {"txn_date": "2025-06-15", "value_date": "2025-06-15", "narration": "Sale", "reference": "", "debit": 0, "credit": 50000, "balance": 50000},
                {"txn_date": "2025-06-20", "value_date": "2025-06-20", "narration": "Rent", "reference": "", "debit": 15000, "credit": 0, "balance": 35000},
                {"txn_date": "2025-07-05", "value_date": "2025-07-05", "narration": "Service", "reference": "", "debit": 0, "credit": 30000, "balance": 65000},
                {"txn_date": "2025-07-10", "value_date": "2025-07-10", "narration": "Utilities", "reference": "", "debit": 5000, "credit": 0, "balance": 60000},
            ]
            await bulk_create_transactions(db, 1, txns)

        asyncio.get_event_loop().run_until_complete(_seed())

    def test_fy_select_has_option(self, client):
        body = client.get("/content?fy=2025").text
        assert "FY 2025-2026" in body

    def test_accounts_table_shows_data(self, client):
        body = client.get("/content?fy=2025").text
        assert "Test Bank" in body
        assert "Test Account" in body
        assert "dashboard-accounts-table" in body

    def test_summary_shows_totals(self, client):
        body = client.get("/content?fy=2025").text
        assert "dashboard-total-income" in body
        assert "dashboard-total-expense" in body
        assert "dashboard-net" in body
        assert "Total Income" in body
        assert "Total Expense" in body
        assert "Net" in body

    def test_month_filter(self, client):
        body = client.get("/content?fy=2025&month=6").text
        assert "Jun" in body

    def test_chart_js_loaded(self, client):
        body = client.get("/content?fy=2025").text
        assert "chart.umd.min.js" in body

    def test_monthly_data_with_fy(self, client):
        body = client.get("/content?fy=2025").text
        assert "chart-income-expense" in body

    def test_pie_chart_sections(self, client):
        body = client.get("/content?fy=2025").text
        assert "chart-top-income" in body
        assert "chart-top-expense" in body


class TestComingSoonPages:

    def test_reports_returns_200(self, client):
        assert client.get("/reports").status_code == 200

    def test_reports_shows_coming_soon(self, client):
        body = client.get("/reports").text
        assert "Coming soon" in body
        assert "Reports" in body

    def test_dashboard_coming_soon_not_shown(self, client):
        assert "Coming soon" not in client.get("/").text
